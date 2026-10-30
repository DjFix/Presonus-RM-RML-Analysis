#include "presonus/uc/data_codecs.hpp"

namespace {
using namespace Presonus::UC;
bool readWord(BufferReader &r, std::uint32_t &v, bool big = false) {
  unsigned char bytes[4];
  if (!r.readRaw(bytes, 4))
    return false;
  v = 0;
  for (unsigned i = 0; i < 4; ++i)
    v |= std::uint32_t(bytes[i]) << (8 * (big ? 3 - i : i));
  return true;
}
bool writeWord(BufferWriter &w, std::uint32_t v, bool big = false) {
  unsigned char bytes[4];
  for (unsigned i = 0; i < 4; ++i)
    bytes[i] = static_cast<unsigned char>(v >> (8 * (big ? 3 - i : i)));
  return w.writeRaw(bytes, 4);
}
template <class T>
bool readBuffer(presonus::uc::DataCodecBindings<T> b, EventItem &item,
                BufferReader &r) {
  std::uint32_t count = 0;
  if (!readWord(r, count))
    return false;
  Core::IO::Buffer &storage = b.storage(b.context, item);
  if (!storage.resize(count))
    return false;
  T &value = b.itemView(b.context, item);
  value.data = storage.getAddress();
  value.sizeBits = count;
  unsigned char scratch = 0;
  return r.readRaw(count == 0 && storage.getAddress() == nullptr
                       ? &scratch
                       : storage.getAddress(),
                   static_cast<int>(count));
}
template <class T>
bool writeBuffer(presonus::uc::DataCodecBindings<T> b, BufferWriter &w,
                 const Event &event) {
  const T &value = b.view(b.context, event);
  if (!writeWord(w, value.sizeBits))
    return false;
  unsigned char scratch = 0;
  return w.writeRaw(value.sizeBits == 0 && value.data == nullptr ? &scratch
                                                                 : value.data,
                    static_cast<int>(value.sizeBits));
}
} // namespace

namespace Presonus::UC {
template <class T, int Type>
bool DataEventClass<T, Type>::readDataBuffer(EventItem &item,
                                             BufferReader &r) const {
  return readBuffer(bindings_, item, r);
}
template <class T, int Type>
bool DataEventClass<T, Type>::writeDataBuffer(BufferWriter &w,
                                              const Event &e) const {
  return writeBuffer(bindings_, w, e);
}
template <class T, int Type>
bool DataEventClass<T, Type>::read(EventItem &item, BufferReader &r) const {
  Event &e = item.getData();
  return bindings_.readHeader(bindings_.context, e, r) &&
         readBuffer(bindings_, item, r);
}
template <class T, int Type>
bool DataEventClass<T, Type>::write(BufferWriter &w, const Event &e) const {
  return EventClass{}.write(w, e) && writeBuffer(bindings_, w, e);
}
template <class T, int Type>
EventItem *DataEventClass<T, Type>::create(const Event &e) const {
  EventItem *item = bindings_.allocate(bindings_.context);
  T &destination = bindings_.itemView(bindings_.context, *item);
  destination = bindings_.view(bindings_.context, e);
  Core::IO::Buffer &storage = bindings_.storage(bindings_.context, *item);
  storage.resize(destination.sizeBits); // Original ignores resize failure.
  if (destination.sizeBits != 0 && destination.sizeBits < 0x80000000u)
    storage.copyFrom(destination.data, destination.sizeBits);
  destination.data =
      storage.getAddress(); // Declared length deliberately retained.
  return item;
}
bool BinaryEventClass::read(EventItem &item, BufferReader &r) const {
  if (!bindings_.readHeader(bindings_.context, item.getData(), r))
    return false;
  BinaryEvent &value = bindings_.view(bindings_.context, item.getData());
  return readWord(r, value.word24, true) && readBuffer(bindings_, item, r);
}
bool BinaryEventClass::write(BufferWriter &w, const Event &e) const {
  if (!EventClass{}.write(w, e))
    return false;
  return writeWord(w, bindings_.view(bindings_.context, e).word24, true) &&
         writeBuffer(bindings_, w, e);
}
bool MessageChunkEventClass::read(EventItem &item, BufferReader &r) const {
  if (!bindings_.readHeader(bindings_.context, item.getData(), r))
    return false;
  MessageChunkEvent &value = bindings_.view(bindings_.context, item.getData());
  return readWord(r, value.word24, true) && readWord(r, value.word28) &&
         readWord(r, value.word32) &&
         DataEventClass<MessageChunkEvent, 17227>{bindings_}.readDataBuffer(
             item, r);
}
bool MessageChunkEventClass::write(BufferWriter &w, const Event &e) const {
  if (!EventClass{}.write(w, e))
    return false;
  const MessageChunkEvent &value = bindings_.view(bindings_.context, e);
  return writeWord(w, value.word24, true) && writeWord(w, value.word28) &&
         writeWord(w, value.word32) &&
         DataEventClass<MessageChunkEvent, 17227>{bindings_}.writeDataBuffer(w,
                                                                             e);
}
template bool
DataEventClass<EncodedMessageEvent<21826>, 21826>::read(EventItem &,
                                                        BufferReader &) const;
template bool
DataEventClass<EncodedMessageEvent<21826>, 21826>::write(BufferWriter &,
                                                         const Event &) const;
template EventItem *
DataEventClass<EncodedMessageEvent<21826>, 21826>::create(const Event &) const;
template bool
DataEventClass<MessageChunkEvent, 17227>::readDataBuffer(EventItem &,
                                                         BufferReader &) const;
template bool
DataEventClass<MessageChunkEvent, 17227>::writeDataBuffer(BufferWriter &,
                                                          const Event &) const;
} // namespace Presonus::UC
