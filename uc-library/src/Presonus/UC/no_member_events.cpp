#include "presonus/uc/no_member_events.hpp"
namespace Presonus::UC {
template <class T, int Type>
bool PrimitiveEventClassNoMembers<T, Type>::write(BufferWriter &,
                                                  const T &) const {
  return true;
}
template <class T, int Type>
bool PrimitiveEventClassNoMembers<T, Type>::read(T &, BufferReader &) const {
  return true;
}
template class PrimitiveEventClassNoMembers<NoOpEvent, 20047>;
template class PrimitiveEventClassNoMembers<DiscoveryLeaveEvent, 17484>;
template class PrimitiveEventClassNoMembers<DiscoveryQueryEvent, 17489>;
template class PrimitiveEventClassNoMembers<KeepAliveEvent, 19265>;
template <>
bool PrimitiveEventClass<NoOpEvent, 20047>::write(BufferWriter &writer,
                                                  const Event &event) const {
  if (!EventClass().write(writer, event))
    return false;
  return callbacks_.write(callbacks_.context, writer, event);
}
template <>
bool PrimitiveEventClass<NoOpEvent, 20047>::read(Event &event,
                                                 BufferReader &reader) const {
  if (!EventClass().read(event, reader))
    return false;
  return callbacks_.read(callbacks_.context, event, reader);
}
template <>
bool PrimitiveEventClass<DiscoveryLeaveEvent, 17484>::write(
    BufferWriter &writer, const Event &event) const {
  if (!EventClass().write(writer, event))
    return false;
  return callbacks_.write(callbacks_.context, writer, event);
}
template <>
bool PrimitiveEventClass<DiscoveryLeaveEvent, 17484>::read(
    Event &event, BufferReader &reader) const {
  if (!EventClass().read(event, reader))
    return false;
  return callbacks_.read(callbacks_.context, event, reader);
}
template <>
bool PrimitiveEventClass<DiscoveryQueryEvent, 17489>::write(
    BufferWriter &writer, const Event &event) const {
  if (!EventClass().write(writer, event))
    return false;
  return callbacks_.write(callbacks_.context, writer, event);
}
template <>
bool PrimitiveEventClass<DiscoveryQueryEvent, 17489>::read(
    Event &event, BufferReader &reader) const {
  if (!EventClass().read(event, reader))
    return false;
  return callbacks_.read(callbacks_.context, event, reader);
}
template <>
bool PrimitiveEventClass<KeepAliveEvent, 19265>::write(
    BufferWriter &writer, const Event &event) const {
  if (!EventClass().write(writer, event))
    return false;
  return callbacks_.write(callbacks_.context, writer, event);
}
template <>
bool PrimitiveEventClass<KeepAliveEvent, 19265>::read(
    Event &event, BufferReader &reader) const {
  if (!EventClass().read(event, reader))
    return false;
  return callbacks_.read(callbacks_.context, event, reader);
}
} // namespace Presonus::UC
