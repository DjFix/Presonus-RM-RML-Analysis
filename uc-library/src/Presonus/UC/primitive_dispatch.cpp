#include "presonus/uc/primitive_dispatch.hpp"
namespace Presonus::UC {
template <class T, int Type>
bool PrimitiveEventClass<T, Type>::write(BufferWriter &writer,
                                         const Event &event) const {
  if (!EventClass().write(writer, event))
    return false;
  return callbacks_.write(callbacks_.context, writer, event);
}
template <class T, int Type>
bool PrimitiveEventClass<T, Type>::read(Event &event,
                                        BufferReader &reader) const {
  if (!EventClass().read(event, reader))
    return false;
  return callbacks_.read(callbacks_.context, event, reader);
}
template class PrimitiveEventClass<UDPMappingEvent, 21837>;
template class PrimitiveEventClass<MidiMessageEvent, 19789>;
template class PrimitiveEventClass<ExtensionQueryEvent, 17745>;
template class PrimitiveEventClass<ParamValueEvent, 20566>;
template class PrimitiveEventClass<ParamStringEvent, 20563>;
template class PrimitiveEventClass<DiscoveryAliveEvent, 17473>;
} // namespace Presonus::UC
