#pragma once
#include "core/public/corehashmap.h"
#include "presonus/uc/data_codecs.hpp"
#include <cstdint>
#include <memory>
#include <stdexcept>
namespace Presonus::UC {
struct LoopbackQueryEvent;
struct LoopbackReplyEvent;
struct MidiLongSysexEvent;
} // namespace Presonus::UC
namespace presonus::uc {
// Explicit independent source-port payload. Tag supplies identity only; this
// neither defines nor replaces the original opaque event or nonowning view.
template <class Tag> struct OwnedDataPayload {
  Presonus::UC::Event header{};
  const void *data = nullptr;
  std::uint32_t sizeBits = 0;
};
// Actual CCL-owned buffers and typed provenance. Original pool/ARM layout and
// default virtual class hierarchy are not claimed. Serialized access only.
template <class Value, int Type, unsigned Words = 0>
class OwnedDataFactoryCodec {
  using Event = Presonus::UC::Event;
  using Item = OwnedCodecItem<Value>;
  using EventItem = Presonus::UC::EventItem;
  using Reader = Presonus::UC::BufferReader;
  using Writer = Presonus::UC::BufferWriter;

public:
  using value_type = Value;
  static constexpr unsigned payload_words = Words;
  OwnedDataFactoryCodec()
      : bindings_(32, hash, nullptr),
        codec_{this, create, clone, write, read, destroy} {}
  OwnedDataFactoryCodec(const OwnedDataFactoryCodec &) = delete;
  OwnedDataFactoryCodec &operator=(const OwnedDataFactoryCodec &) = delete;
  void bind(const Value &value) {
    if (!bindings_.replaceValue(&value.header, &value))
      bindings_.add(&value.header, &value);
  }
  void unbind(const Value &value) { bindings_.remove(&value.header); }
  // Explicit typed provenance only; no header/container cast. Referents must
  // outlive bindings. Factory-produced values require bind(value) before reuse.
  bool resolve(const Event &event, const Value *&value) const {
    value = nullptr;
    return bindings_.get(value, &event);
  }
  const FactoryCodec &codec() const { return codec_; }
  void registerIn(FactoryRegistry &registry) { registry.append(Type, &codec_); }
  static constexpr int type = Type;

private:
  static int hash(const Event *const &key, int size) {
    return int((reinterpret_cast<std::uintptr_t>(key) >> 3) % unsigned(size));
  }
  static OwnedDataFactoryCodec &self(void *p) {
    return *static_cast<OwnedDataFactoryCodec *>(p);
  }
  const Value *find(const Event &event) const {
    const Value *value = nullptr;
    return bindings_.get(value, &event) ? value : nullptr;
  }
  static EventItem *create(void *) {
    auto item = std::make_unique<Item>();
    item->value.header.type = Type;
    // Original ARM default event size words: common16 + pointer4 + length4,
    // with one Binary or three MessageChunk words appended. Not sizeof(native).
    item->value.header.reserved04 = 24 + Words * 4;
    return item.release();
  }
  static EventItem *clone(void *p, const Event &event) {
    const auto *value = self(p).find(event);
    if (!value)
      return nullptr;
    auto item = std::unique_ptr<Item>(static_cast<Item *>(create(p)));
    item->value = *value;
    item->storage.resize(value->sizeBits);
    if (value->sizeBits && value->sizeBits < 0x80000000u)
      item->storage.copyFrom(value->data, value->sizeBits);
    item->value.data = item->storage.getAddress();
    return item.release();
  }
  static bool readWord(Reader &r, std::uint32_t &value, bool big = false) {
    unsigned char bytes[4];
    if (!r.readRaw(bytes, 4))
      return false;
    value = 0;
    for (unsigned i = 0; i != 4; ++i)
      value |= std::uint32_t(bytes[i]) << (8 * (big ? 3 - i : i));
    return true;
  }
  static bool writeWord(Writer &w, std::uint32_t value, bool big = false) {
    unsigned char bytes[4];
    for (unsigned i = 0; i != 4; ++i)
      bytes[i] = static_cast<unsigned char>(value >> (8 * (big ? 3 - i : i)));
    return w.writeRaw(bytes, 4);
  }
  static bool write(void *p, Writer &w, const Event &event) {
    const auto *value = self(p).find(event);
    if (!value || !Presonus::UC::EventClass{}.write(w, event))
      return false;
    if constexpr (Words > 0)
      if (!writeWord(w, value->word24, true))
        return false;
    if constexpr (Words > 1)
      if (!writeWord(w, value->word28) || !writeWord(w, value->word32))
        return false;
    if (!writeWord(w, value->sizeBits))
      return false;
    unsigned char scratch = 0;
    return w.writeRaw(value->sizeBits == 0 && !value->data ? &scratch
                                                           : value->data,
                      static_cast<int>(value->sizeBits));
  }
  static bool read(void *, EventItem *base, Reader &r) {
    auto *item = dynamic_cast<Item *>(base);
    if (!item || !Presonus::UC::EventClass{}.read(item->value.header, r))
      return false;
    if constexpr (Words > 0)
      if (!readWord(r, item->value.word24, true))
        return false;
    if constexpr (Words > 1)
      if (!readWord(r, item->value.word28) || !readWord(r, item->value.word32))
        return false;
    std::uint32_t count = 0;
    if (!readWord(r, count) || !item->storage.resize(count))
      return false;
    item->value.data = item->storage.getAddress();
    item->value.sizeBits = count;
    unsigned char scratch = 0;
    return r.readRaw(
        count == 0 && !item->value.data ? &scratch : item->storage.getAddress(),
        static_cast<int>(count));
  }
  static void destroy(void *, EventItem *item) { delete item; }
  Core::HashMap<const Event *, const Value *> bindings_;
  FactoryCodec codec_;
};
using BinaryFactoryCodec =
    OwnedDataFactoryCodec<Presonus::UC::BinaryEvent, 16975, 1>;
using MessageChunkFactoryCodec =
    OwnedDataFactoryCodec<Presonus::UC::MessageChunkEvent, 17227, 3>;
template <int Type>
using EncodedDataFactoryCodec =
    OwnedDataFactoryCodec<Presonus::UC::EncodedMessageEvent<Type>, Type>;
using LoopbackQueryDataFactoryCodec =
    OwnedDataFactoryCodec<OwnedDataPayload<Presonus::UC::LoopbackQueryEvent>,
                          19537>;
using LoopbackReplyDataFactoryCodec =
    OwnedDataFactoryCodec<OwnedDataPayload<Presonus::UC::LoopbackReplyEvent>,
                          19538>;
using MidiLongSysexDataFactoryCodec =
    OwnedDataFactoryCodec<OwnedDataPayload<Presonus::UC::MidiLongSysexEvent>,
                          21324>;
} // namespace presonus::uc
