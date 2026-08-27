"""
Inference Engine Completion
Rebuild 3: Unification & Variable Binding

Completes the inference engine with unification algorithm
and variable binding for symbolic reasoning.
"""

from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import uuid


@dataclass
class Substitution:
    """Variable substitution mapping"""
    bindings: Dict[str, Any]
    
    def apply(self, term: Any) -> Any:
        """Apply substitution to a term"""
        if isinstance(term, str) and term.startswith('?'):
            return self.bindings.get(term, term)
        elif isinstance(term, dict):
            return {k: self.apply(v) for k, v in term.items()}
        elif isinstance(term, list):
            return [self.apply(t) for t in term]
        return term
    
    def compose(self, other: 'Substitution') -> 'Substitution':
        """Compose two substitutions"""
        result = self.bindings.copy()
        for var, val in other.bindings.items():
            result[var] = self.apply(val)
        return Substitution(result)


class Unifier:
    """
    Unification algorithm for symbolic reasoning.
    Finds substitutions that make two terms identical.
    """
    
    def __init__(self):
        self.unification_count = 0
    
    def unify(self, term1: Any, term2: Any, subst: Optional[Substitution] = None) -> Optional[Substitution]:
        """
        Unify two terms.
        Returns substitution if successful, None if no unification possible.
        """
        if subst is None:
            subst = Substitution({})
        
        # Apply current substitution
        term1 = subst.apply(term1)
        term2 = subst.apply(term2)
        
        # If identical, unification succeeds
        if term1 == term2:
            return subst
        
        # If term1 is variable
        if isinstance(term1, str) and term1.startswith('?'):
            if self._occurs_check(term1, term2):
                return None  # Occurs check failed
            return Substitution({**subst.bindings, term1: term2})
        
        # If term2 is variable
        if isinstance(term2, str) and term2.startswith('?'):
            if self._occurs_check(term2, term1):
                return None
            return Substitution({**subst.bindings, term2: term1})
        
        # If both are dicts
        if isinstance(term1, dict) and isinstance(term2, dict):
            if set(term1.keys()) != set(term2.keys()):
                return None
            
            for key in term1.keys():
                subst = self.unify(term1[key], term2[key], subst)
                if subst is None:
                    return None
            return subst
        
        # If both are lists
        if isinstance(term1, list) and isinstance(term2, list):
            if len(term1) != len(term2):
                return None
            
            for t1, t2 in zip(term1, term2):
                subst = self.unify(t1, t2, subst)
                if subst is None:
                    return None
            return subst
        
        # No unification possible
        return None
    
    def _occurs_check(self, var: str, term: Any) -> bool:
        """Check if variable occurs in term"""
        if isinstance(term, str):
            return var == term
        elif isinstance(term, dict):
            return any(self._occurs_check(var, v) for v in term.values())
        elif isinstance(term, list):
            return any(self._occurs_check(var, t) for t in term)
        return False


class VariableBinder:
    """
    Manages variable binding during inference.
    Tracks bound variables and their domains.
    """
    
    def __init__(self):
        self.bindings: Dict[str, Any] = {}
        self.domains: Dict[str, List[Any]] = {}
    
    def bind(self, var: str, value: Any) -> bool:
        """Bind a variable to a value"""
        if var in self.bindings:
            return self.bindings[var] == value
        self.bindings[var] = value
        return True
    
    def lookup(self, var: str) -> Optional[Any]:
        """Look up a variable binding"""
        return self.bindings.get(var)
    
    def set_domain(self, var: str, domain: List[Any]) -> None:
        """Set the domain of possible values for a variable"""
        self.domains[var] = domain
    
    def get_domain(self, var: str) -> List[Any]:
        """Get domain of a variable"""
        return self.domains.get(var, [])
    
    def backtrack(self) -> None:
        """Backtrack: undo last bindings"""
        # TODO: Implement backtracking with choice points
        pass


class EnhancedInferenceEngine:
    """
    Enhanced inference engine with unification and variable binding.
    """
    
    def __init__(self, knowledge_base):
        self.kb = knowledge_base
        self.unifier = Unifier()
        self.binder = VariableBinder()
    
    def query(self, goal: Dict[str, Any]) -> List[Substitution]:
        """
        Query the knowledge base.
        Returns all substitutions that satisfy the goal.
        """
        solutions = []
        self._prove_goal(goal, Substitution({}), solutions)
        return solutions
    
    def _prove_goal(self, goal: Dict[str, Any], subst: Substitution, solutions: List[Substitution]) -> None:
        """
        Recursively prove a goal.
        Accumulates solutions.
        """
        # Check if goal is in KB
        for fact in self.kb.facts.values():
            fact_dict = {
                "subject": fact.subject.name,
                "predicate": fact.predicate,
                "object": fact.object,
            }
            
            # Try to unify with fact
            new_subst = self.unifier.unify(goal, fact_dict, subst)
            if new_subst is not None:
                solutions.append(new_subst)
        
        # Try to prove using rules
        for rule in self.kb.rules.values():
            # Unify goal with rule conclusion
            rule_conclusion = {
                "subject": rule.conclusion.subject.name,
                "predicate": rule.conclusion.predicate,
                "object": rule.conclusion.object,
            }
            
            new_subst = self.unifier.unify(goal, rule_conclusion, subst)
            if new_subst is not None:
                # Recursively prove rule conditions
                self._prove_conditions(rule.conditions, new_subst, solutions)
    
    def _prove_conditions(self, conditions: List, subst: Substitution, solutions: List[Substitution]) -> None:
        """
        Prove a list of conditions.
        All conditions must be satisfied.
        """
        if not conditions:
            solutions.append(subst)
            return
        
        condition = conditions[0]
        remaining = conditions[1:]
        
        # Prove first condition
        for new_subst in self.query(condition):
            # Prove remaining conditions with new substitution
            self._prove_conditions(remaining, new_subst, solutions)
