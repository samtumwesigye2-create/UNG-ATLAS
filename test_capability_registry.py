from capability_registry import CapabilityRegistry

def test_register_and_discover():
    r=CapabilityRegistry()
    r.register('NEXUS','Integration','https://nexus.example',['message-routing','vendor-connectors'])
    r.register('PULSAR','Relay','https://pulsar.example',['message-routing','durable-delivery'])
    assert r.get('UNG-NEXUS').system_id == 'UNG-NEXUS'
    assert [x.system_id for x in r.discover('message-routing')] == ['UNG-NEXUS','UNG-PULSAR']
    assert [x.system_id for x in r.discover('durable-delivery')] == ['UNG-PULSAR']
