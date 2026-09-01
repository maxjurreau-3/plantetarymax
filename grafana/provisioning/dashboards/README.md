# Documentation: Grafana provisioning behavior
#
# We provision the Prometheus datasource from /etc/grafana/provisioning/datasources/datasource.yml
# Dashboards are provided from ./grafana/dashboards and mounted at /var/lib/grafana/dashboards.
# The provider sets `allowUiUpdates: true` so that edits made in the Grafana UI are stored
# in the Grafana sqlite/postgres DB (persisted in the grafana-data volume) and not overwritten
# by the read-only dashboard files after initial provisioning.
#
# Behavior notes:
# - On first startup Grafana will load dashboards from the file path into the DB.
# - Because allowUiUpdates=true, subsequent UI edits are permitted and will persist in the DB.
# - If you remove the dashboard file from the provisioning folder, the DB copy will remain.
# - If you update the dashboard file on disk and restart Grafana, the provisioning will not
#   overwrite UI edits (allowUiUpdates prevents overwrites). To force an update, either remove
#   the managed dashboard from the DB or change provisioning settings.
