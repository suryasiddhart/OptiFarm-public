{{- define "mosquitto.name" -}}
{{- default "mosquitto" .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "mosquitto.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default "mosquitto" .Values.nameOverride }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{- define "mosquitto.labels" -}}
app.kubernetes.io/name: {{ include "mosquitto.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app: mosquitto
{{- end }}
