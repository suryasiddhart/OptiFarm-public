{{- define "ingest.name" -}}
{{- default "ingest" .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "ingest.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default "ingest" .Values.nameOverride }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{- define "ingest.labels" -}}
app.kubernetes.io/name: {{ include "ingest.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app: ingest
{{- end }}
