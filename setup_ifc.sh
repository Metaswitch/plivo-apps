# Configures Clearwater IFC to invoke Plivo app server as a terminating AS.
# Must be run from a node which can access Homestead API.  Syntax is
#   ./setup_ifc.sh <Homestead host name> <public user identity> <Plivo SIP URI>
# For example
#   ./setup_ifc.sh hs.cw-ngv.com sip:2015550001@cw-ngv.com sip:plivo.cw-ngv.com:5058
#
{ cat <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<ServiceProfile>
  <InitialFilterCriteria>
    <Priority>1</Priority>
    <TriggerPoint>
      <ConditionTypeCNF>1</ConditionTypeCNF>
      <SPT>
        <ConditionNegated>0</ConditionNegated>
        <Group>0</Group>
        <Method>INVITE</Method>
        <Extension></Extension>
      </SPT>
      <SPT>
        <ConditionNegated>0</ConditionNegated>
        <Group>1</Group>
        <SessionCase>2</SessionCase>
        <Extension></Extension>
      </SPT>
    </TriggerPoint>
    <ApplicationServer>
      <ServerName>$3</ServerName>
      <DefaultHandling>0</DefaultHandling>
    </ApplicationServer>
  </InitialFilterCriteria>
</ServiceProfile>
EOF
} | curl -X PUT http://$1:8888/filtercriteria/$2 --data-binary @-
