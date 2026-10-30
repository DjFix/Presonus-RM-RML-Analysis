#pragma once
#include "presonus/uc/discovery_events.hpp"
#include "presonus/uc/transport_events.hpp"
namespace presonus::uc {
// Independent portable representation of the original typed virtual slots.
struct PrimitivePayloadCallbacks {
  void *context;
  bool (*write)(void *, Presonus::UC::BufferWriter &,
                const Presonus::UC::Event &);
  bool (*read)(void *, Presonus::UC::Event &, Presonus::UC::BufferReader &);
};
} // namespace presonus::uc
namespace Presonus::UC {
template <class T, int Type> class PrimitiveEventClass {
public:
  // New explicit binding constructor; original inheritance/vtable/layout,
  // default construction, create/pool and ownership remain unrecovered.
  explicit PrimitiveEventClass(
      presonus::uc::PrimitivePayloadCallbacks callbacks)
      : callbacks_(callbacks) {}
  bool write(BufferWriter &, const Event &) const;
  bool read(Event &, BufferReader &) const;

private:
  presonus::uc::PrimitivePayloadCallbacks callbacks_;
};
extern template class PrimitiveEventClass<UDPMappingEvent, 21837>;
extern template class PrimitiveEventClass<MidiMessageEvent, 19789>;
extern template class PrimitiveEventClass<ExtensionQueryEvent, 17745>;
extern template class PrimitiveEventClass<ParamValueEvent, 20566>;
extern template class PrimitiveEventClass<ParamStringEvent, 20563>;
extern template class PrimitiveEventClass<DiscoveryAliveEvent, 17473>;
} // namespace Presonus::UC
