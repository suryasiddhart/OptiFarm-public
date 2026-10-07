{{- define "timescaledb.name" -}}
{{- default "timescaledb" .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "timescaledb.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default "timescaledb" .Values.nameOverride }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{- define "timescaledb.labels" -}}
app.kubernetes.io/name: {{ include "timescaledb.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app: timescaledb
{{- end }}
