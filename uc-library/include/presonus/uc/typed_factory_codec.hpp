#pragma once
#include "presonus/uc/event_factory.hpp"
#include "presonus/uc/primitive_dispatch.hpp"
#include <map>
namespace presonus::uc {
// Independent portable allocation/binding adapter, not original addClass,
// DataItem/PooledDataItem creation, destruction, inheritance or allocator ABI.
template <class T> struct TypedEventItem : Presonus::UC::EventItem {
  T value;
  Presonus::UC::Event &getData() override { return value.header; }
};
template <class T, class Codec, int Type> class TypedFactoryCodec {
  using Item = TypedEventItem<T>;
  using Event = Presonus::UC::Event;
  using EventItem = Presonus::UC::EventItem;
  using Writer = Presonus::UC::BufferWriter;
  using Reader = Presonus::UC::BufferReader;

public:
  TypedFactoryCodec()
      : dispatch_({this, writePayload, readPayload}),
        codec_{this, create, clone, write, read, destroy} {}
  TypedFactoryCodec(const TypedFactoryCodec &) = delete;
  TypedFactoryCodec &operator=(const TypedFactoryCodec &) = delete;
  // Bound outbound objects must outlive their binding and all factory calls.
  // Items returned by read/create/createType are NOT automatically bound.
  // bind(item.value) before writing/cloning that item, and unbind(item.value)
  // before deleting it (directly or through codec.destroy). Leaving a binding
  // to a destroyed object violates this independent adapter's lifetime
  // contract. Header address is explicit: no invented inheritance or unsafe
  // downcast.
  void bind(const T &value) { bound_[&value.header] = &value; }
  void unbind(const T &value) { bound_.erase(&value.header); }
  const FactoryCodec &codec() const { return codec_; }
  void registerIn(FactoryRegistry &registry) { registry.append(Type, &codec_); }

private:
  static TypedFactoryCodec &self(void *p) {
    return *static_cast<TypedFactoryCodec *>(p);
  }
  static EventItem *create(void *) {
    auto *item = new Item;
    item->value.header.type = Type;
    return item;
  }
  static EventItem *clone(void *p, const Event &event) {
    auto &s = self(p);
    auto found = s.bound_.find(&event);
    if (found == s.bound_.end())
      return nullptr;
    auto *item = new Item;
    item->value = *found->second;
    return item;
  }
  static bool write(void *p, Writer &writer, const Event &event) {
    return self(p).dispatch_.write(writer, event);
  }
  static bool read(void *p, EventItem *base, Reader &reader) {
    auto &s = self(p);
    auto *item = dynamic_cast<Item *>(base);
    if (!item)
      return false;
    struct Restore {
      T *&slot;
      T *old;
      ~Restore() { slot = old; }
    } restore{s.active_, s.active_};
    s.active_ = &item->value;
    return s.dispatch_.read(item->value.header, reader);
  }
  static void destroy(void *, EventItem *item) { delete item; }
  static bool writePayload(void *p, Writer &writer, const Event &event) {
    auto &s = self(p);
    auto found = s.bound_.find(&event);
    return found != s.bound_.end() && Codec().write(writer, *found->second);
  }
  static bool readPayload(void *p, Event &event, Reader &reader) {
    auto &s = self(p);
    return s.active_ && &s.active_->header == &event &&
           Codec().read(*s.active_, reader);
  }
  std::map<const Event *, const T *> bound_;
  T *active_ = nullptr;
  Presonus::UC::PrimitiveEventClass<T, Type> dispatch_;
  FactoryCodec codec_;
};
using UDPMappingFactoryCodec =
    TypedFactoryCodec<Presonus::UC::UDPMappingEvent,
                      Presonus::UC::UDPMappingEventClass, 21837>;
using MidiMessageFactoryCodec =
    TypedFactoryCodec<Presonus::UC::MidiMessageEvent,
                      Presonus::UC::MidiMessageEventClass, 19789>;
using ExtensionQueryFactoryCodec =
    TypedFactoryCodec<Presonus::UC::ExtensionQueryEvent,
                      Presonus::UC::ExtensionQueryEventClass, 17745>;
using ParamValueFactoryCodec =
    TypedFactoryCodec<Presonus::UC::ParamValueEvent,
                      Presonus::UC::ParamValueEventClass, 20566>;
using ParamStringFactoryCodec =
    TypedFactoryCodec<Presonus::UC::ParamStringEvent,
                      Presonus::UC::ParamStringEventClass, 20563>;
using DiscoveryAliveFactoryCodec =
    TypedFactoryCodec<Presonus::UC::DiscoveryAliveEvent,
                      Presonus::UC::DiscoveryAliveEventClass, 17473>;
} // namespace presonus::uc
