#pragma once
#include "presonus/uc/typed_factory_codec.hpp"
namespace Presonus::UC {
// Portable header storage. Original inheritance/layout/constructor ABI remains
// unproved; these types have no observed payload fields.
struct NoOpEvent {
  Event header;
};
struct DiscoveryLeaveEvent {
  Event header;
};
struct DiscoveryQueryEvent {
  Event header;
};
struct KeepAliveEvent {
  Event header;
};
template <class T, int Type> class PrimitiveEventClassNoMembers {
public:
  // Original methods return1 without accessing event or buffer. These are
  // payload no-ops; PrimitiveEventClass handles the separate common header.
  // Original non-template return spelling is unencoded; bool matches0/1.
  bool write(BufferWriter &, const T &) const;
  bool read(T &, BufferReader &) const;
};
extern template class PrimitiveEventClassNoMembers<NoOpEvent, 20047>;
extern template class PrimitiveEventClassNoMembers<DiscoveryLeaveEvent, 17484>;
extern template class PrimitiveEventClassNoMembers<DiscoveryQueryEvent, 17489>;
extern template class PrimitiveEventClassNoMembers<KeepAliveEvent, 19265>;
template <>
bool PrimitiveEventClass<NoOpEvent, 20047>::write(BufferWriter &,
                                                  const Event &) const;
template <>
bool PrimitiveEventClass<NoOpEvent, 20047>::read(Event &, BufferReader &) const;
template <>
bool PrimitiveEventClass<DiscoveryLeaveEvent, 17484>::write(
    BufferWriter &, const Event &) const;
template <>
bool PrimitiveEventClass<DiscoveryLeaveEvent, 17484>::read(
    Event &, BufferReader &) const;
template <>
bool PrimitiveEventClass<DiscoveryQueryEvent, 17489>::write(
    BufferWriter &, const Event &) const;
template <>
bool PrimitiveEventClass<DiscoveryQueryEvent, 17489>::read(
    Event &, BufferReader &) const;
template <>
bool PrimitiveEventClass<KeepAliveEvent, 19265>::write(BufferWriter &,
                                                       const Event &) const;
template <>
bool PrimitiveEventClass<KeepAliveEvent, 19265>::read(Event &,
                                                      BufferReader &) const;
} // namespace Presonus::UC
namespace presonus::uc {
using NoOpFactoryCodec = TypedFactoryCodec<
    Presonus::UC::NoOpEvent,
    Presonus::UC::PrimitiveEventClassNoMembers<Presonus::UC::NoOpEvent, 20047>,
    20047>;
using DiscoveryLeaveFactoryCodec =
    TypedFactoryCodec<Presonus::UC::DiscoveryLeaveEvent,
                      Presonus::UC::PrimitiveEventClassNoMembers<
                          Presonus::UC::DiscoveryLeaveEvent, 17484>,
                      17484>;
using DiscoveryQueryFactoryCodec =
    TypedFactoryCodec<Presonus::UC::DiscoveryQueryEvent,
                      Presonus::UC::PrimitiveEventClassNoMembers<
                          Presonus::UC::DiscoveryQueryEvent, 17489>,
                      17489>;
using KeepAliveFactoryCodec =
    TypedFactoryCodec<Presonus::UC::KeepAliveEvent,
                      Presonus::UC::PrimitiveEventClassNoMembers<
                          Presonus::UC::KeepAliveEvent, 19265>,
                      19265>;
} // namespace presonus::uc
