#include "presonus/uc/event_factory.hpp"
#include <cstring>

namespace {
int typeBits(std::uint32_t value) {
  static_assert(sizeof(int) == 4, "32-bit original type bits required");
  int result;
  std::memcpy(&result, &value, 4);
  return result;
}
} // namespace
namespace presonus::uc {
void FactoryRegistry::append(int type, const FactoryCodec *codec) {
  if (sourceBackendAppend) {
    sourceBackendAppend(sourceBackendContext, type, codec);
    return;
  }
  buckets[Presonus::UC::EventFactory::hashEventType(type, modulus)].push_back(
      {type, codec});
}
} // namespace presonus::uc
namespace Presonus::UC {
int EventFactory::hashEventType(const int &type, int modulus) {
  return type % modulus;
}
const presonus::uc::FactoryCodec *EventFactory::find(int type) const {
  if (registry_.sourceBackendGet) {
    const presonus::uc::FactoryCodec *codec = nullptr;
    if (registry_.sourceBackendGet(registry_.sourceBackendContext, codec, type))
      return codec;
    return registry_.fallback;
  }
  const auto bucket =
      registry_.buckets.find(hashEventType(type, registry_.modulus));
  if (bucket != registry_.buckets.end())
    for (const auto &entry : bucket->second)
      if (entry.type == type)
        return entry.codec;
  return registry_.fallback;
}
EventItem *EventFactory::create(const Event &event) {
  const auto *codec = find(typeBits(event.type));
  return codec ? codec->clone(codec->context, event) : nullptr;
}
EventItem *EventFactory::createType(int type) {
  const auto *codec = find(type);
  return codec ? codec->create(codec->context) : nullptr;
}
bool EventFactory::write(BufferWriter &writer, const Event &event) {
  const auto *codec = find(typeBits(event.type));
  if (!codec)
    return false;
  codec->write(codec->context, writer, event);
  // Original factory ignores the selected codec's write result.
  return true;
}
int EventFactory::write(char *data, int capacity, const Event &event) {
  BufferWriter writer(data, capacity);
  return write(writer, event) ? writer.position() : -1;
}
EventItem *EventFactory::read(BufferReader &reader) {
  unsigned char tag[2]{};
  int type = 0;
  // Short tag is still looked up as type zero, with unchanged cursor.
  if (reader.readRaw(tag, 2))
    type = (int(tag[0]) << 8) | int(tag[1]);
  const auto *codec = find(type);
  if (!codec)
    return nullptr;
  EventItem *item = codec->create(codec->context);
  if (codec->read(codec->context, item, reader))
    return item;
  if (item)
    codec->destroy(codec->context, item);
  return nullptr;
}
EventItem *EventFactory::read(const char *data, int capacity) {
  BufferReader reader(data, capacity);
  return read(reader);
}
} // namespace Presonus::UC
