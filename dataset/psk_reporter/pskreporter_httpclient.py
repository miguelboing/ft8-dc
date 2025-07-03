import requests
import pandas as pd
from io import StringIO

url = "https://retrieve.pskreporter.info/query"
params = {
        "senderCallsign" : "M7LSI",
        "time": 30,
}

r = requests.get(url, params=params)

# If the XML is HTML-escaped (e.g., &lt; and &gt;), decode it first
xml_string = r.text.replace("&lt;", "<").replace("&gt;", ">")

# Reports that contains the given callsign.
df_reception_report = pd.read_xml(StringIO(xml_string), xpath=".//receptionReport")

# Calssigns that were recently reported as active.
df_active_cs = pd.read_xml(StringIO(xml_string), xpath=".//activeCallsign")

# This are the stations that are currently active.
df_active_receiver = pd.read_xml(StringIO(xml_string), xpath=".//activeReceiver")

# Contains the senderCallsign and the most recent unix epoch of when a transmission from senderCallsign was reported.
df_sender_search = pd.read_xml(StringIO(xml_string), xpath=".//senderSearch")

# Unique identifier for the PSK Reporter request, not really useful for the dataset.
df_last_sequence_number = pd.read_xml(StringIO(xml_string), xpath=".//lastSequenceNumber")

# Unix epoch of the last report contained in this response.
df_max_flow_start_seconds = pd.read_xml(StringIO(xml_string), xpath=".//maxFlowStartSeconds")

df_reception_report.to_csv("reception_report.csv")
df_active_cs.to_csv("active_cs.csv")
df_active_receiver.to_csv("active_receiver.csv")
df_last_sequence_number.to_csv("df_last_sequence_number.csv")
df_max_flow_start_seconds.to_csv("df_max_flow_start_seconds.csv")
