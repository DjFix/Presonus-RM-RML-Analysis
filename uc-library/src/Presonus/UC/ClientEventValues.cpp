#include "core/public/corehashmap.h"
#include "presonus/uc/ccl_bindings.hpp"
#include "presonus/uc/client_event_values.hpp"
#include <cstddef>
#include <type_traits>
#include <utility>
namespace presonus::uc {
namespace UC = Presonus::UC;
namespace {
// These assertions concern ONLY the existing source-owned value types. No
// original layout/inheritance is inferred, and no Event-to-T cast is used.
#define SOURCE_HEADER(T)                                                       \
  static_assert(std::is_standard_layout_v<UC::T> &&                            \
                offsetof(UC::T, header) == 0)
SOURCE_HEADER(ParamValueEvent);
SOURCE_HEADER(ParamStringEvent);
SOURCE_HEADER(ParamColorEvent);
SOURCE_HEADER(ParamRangeEvent);
SOURCE_HEADER(ParamStringListEvent);
SOURCE_HEADER(MeterEvent8);
SOURCE_HEADER(MeterEvent16);
#undef SOURCE_HEADER
struct OriginRecord {
  const void *value = nullptr;
  EventOrigins::Kind kind = EventOrigins::Kind::None;
  std::uint32_t tag = 0;
  std::uint64_t serial = 0;
  bool operator==(const OriginRecord &other) const {
    return value == other.value && kind == other.kind && tag == other.tag &&
           serial == other.serial;
  }
};
int originHash(const UC::Event *const &key, int size) {
  return int((reinterpret_cast<std::uintptr_t>(key) >> 3) %
             std::uintptr_t(size));
}
template <class T> UC::ParamEvent paramView(const T &value) {
  return {value.header, value.path, value.index, ParamPayload{&value}};
}
template <class T> UC::MeterEvent meterView(const T &value) {
  return {value.header,   value.keyBits,       value.source,
          value.count,    value.recordCount,   value.reserved25,
          value.records,  value.data.data(),   value.data.size(),
          T::sampleWidth, MeterPayload{&value}};
}
} // namespace
struct EventOrigins::State {
  Core::HashMap<const UC::Event *, OriginRecord> entries{32, originHash};
  std::uint64_t next = 0;
  void remove(const UC::Event *header, std::uint64_t serial) {
    OriginRecord record;
    if (entries.get(record, header) && record.serial == serial)
      entries.remove(header);
  }
};
EventOrigins::EventOrigins() : state_(std::make_shared<State>()) {}
EventOrigins::Binding::Binding(std::weak_ptr<State> state,
                               const UC::Event *header, std::uint64_t serial)
    : state_(std::move(state)), header_(header), serial_(serial) {}
EventOrigins::Binding::Binding(Binding &&other) noexcept {
  *this = std::move(other);
}
EventOrigins::Binding &
EventOrigins::Binding::operator=(Binding &&other) noexcept {
  if (this != &other) {
    reset();
    state_ = std::move(other.state_);
    header_ = std::exchange(other.header_, nullptr);
    serial_ = std::exchange(other.serial_, 0);
  }
  return *this;
}
EventOrigins::Binding::~Binding() { reset(); }
void EventOrigins::Binding::reset() {
  if (auto state = state_.lock())
    state->remove(header_, serial_);
  state_.reset();
  header_ = nullptr;
  serial_ = 0;
}
EventOrigins::Binding::operator bool() const {
  auto state = state_.lock();
  OriginRecord record;
  return state && header_ && state->entries.get(record, header_) &&
         record.serial == serial_ && header_->type == record.tag;
}
EventOrigins::Binding EventOrigins::bindRaw(const UC::Event *header,
                                            const void *value, Kind kind,
                                            std::uint32_t tag) {
  if (!header || !value || header->type != tag)
    return {};
  OriginRecord existing;
  if (state_->entries.get(existing, header))
    return {};
  if (++state_->next == 0)
    ++state_->next;
  OriginRecord record{value, kind, tag, state_->next};
  state_->entries.add(header, record);
  return Binding(state_, header, record.serial);
}
EventOrigins::Binding EventOrigins::bind(const UC::ParamValueEvent &value) {
  return bindRaw(&value.header, &value, Kind::Value, 20566);
}
EventOrigins::Binding EventOrigins::bind(const UC::ParamStringEvent &value) {
  return bindRaw(&value.header, &value, Kind::String, 20563);
}
EventOrigins::Binding EventOrigins::bind(const UC::ParamColorEvent &value) {
  return bindRaw(&value.header, &value, Kind::Color, 20547);
}
EventOrigins::Binding EventOrigins::bind(const UC::ParamRangeEvent &value) {
  return bindRaw(&value.header, &value, Kind::Range, 20562);
}
EventOrigins::Binding
EventOrigins::bind(const UC::ParamStringListEvent &value) {
  return bindRaw(&value.header, &value, Kind::StringList, 20556);
}
EventOrigins::Binding EventOrigins::bind(const UC::MeterEvent8 &value) {
  return bindRaw(&value.header, &value, Kind::Meter8, 19778);
}
EventOrigins::Binding EventOrigins::bind(const UC::MeterEvent16 &value) {
  return bindRaw(&value.header, &value, Kind::Meter16, 19795);
}
EventOrigins::Binding EventOrigins::bindItem(UC::EventItem &item) {
  if (auto *typed =
          dynamic_cast<TypedEventItem<UC::ParamValueEvent> *>(&item)) {
    if (&item.getData() != &typed->value.header)
      return {};
    return bind(typed->value);
  }
  if (auto *typed =
          dynamic_cast<TypedEventItem<UC::ParamStringEvent> *>(&item)) {
    if (&item.getData() != &typed->value.header)
      return {};
    return bind(typed->value);
  }
  if (auto *typed =
          dynamic_cast<TypedEventItem<UC::ParamColorEvent> *>(&item)) {
    if (&item.getData() != &typed->value.header)
      return {};
    return bind(typed->value);
  }
  if (auto *typed =
          dynamic_cast<TypedEventItem<UC::ParamRangeEvent> *>(&item)) {
    if (&item.getData() != &typed->value.header)
      return {};
    return bind(typed->value);
  }
  if (auto *typed =
          dynamic_cast<TypedEventItem<UC::ParamStringListEvent> *>(&item)) {
    if (&item.getData() != &typed->value.header)
      return {};
    return bind(typed->value);
  }
  if (auto *typed = dynamic_cast<TypedEventItem<UC::MeterEvent8> *>(&item)) {
    if (&item.getData() != &typed->value.header)
      return {};
    return bind(typed->value);
  }
  if (auto *typed = dynamic_cast<TypedEventItem<UC::MeterEvent16> *>(&item)) {
    if (&item.getData() != &typed->value.header)
      return {};
    return bind(typed->value);
  }
  return {};
}
const void *EventOrigins::typed(const UC::Event *header, Kind kind) const {
  OriginRecord record;
  // Never dereference an unbound header: even an old address after item
  // deletion is rejected before any read. The binding owner guarantees live
  // typed storage.
  if (!header || !state_->entries.get(record, header) || record.kind != kind)
    return nullptr;
  return header->type == record.tag ? record.value : nullptr;
}
std::optional<UC::ParamEvent>
EventOrigins::param(const UC::Event *header) const {
  if (const void *value = typed(header, Kind::Value))
    return paramView(*static_cast<const UC::ParamValueEvent *>(value));
  if (const void *value = typed(header, Kind::String))
    return paramView(*static_cast<const UC::ParamStringEvent *>(value));
  if (const void *value = typed(header, Kind::Color))
    return paramView(*static_cast<const UC::ParamColorEvent *>(value));
  if (const void *value = typed(header, Kind::Range))
    return paramView(*static_cast<const UC::ParamRangeEvent *>(value));
  if (const void *value = typed(header, Kind::StringList))
    return paramView(*static_cast<const UC::ParamStringListEvent *>(value));
  return std::nullopt;
}
std::optional<UC::MeterEvent>
EventOrigins::meter(const UC::Event *header) const {
  if (const void *value = typed(header, Kind::Meter8))
    return meterView(*static_cast<const UC::MeterEvent8 *>(value));
  if (const void *value = typed(header, Kind::Meter16))
    return meterView(*static_cast<const UC::MeterEvent16 *>(value));
  return std::nullopt;
}
int EventOrigins::count() const { return state_->entries.count(); }
namespace {
template <class T, int Tag> struct TrackedItem final : TypedEventItem<T> {
  EventOrigins::Binding origin;
  explicit TrackedItem(EventOrigins &origins) {
    this->value.header.type = Tag;
    origin = origins.bind(this->value);
  }
  // origin is destroyed before the typed base/value, including direct virtual
  // delete and EventFactory read-failure cleanup. No payload copy is involved.
};
template <class T, class Codec, int Tag, EventOrigins::Kind Kind>
class TrackedCodec {
  EventOrigins &origins_;
  TypedFactoryCodec<T, Codec, Tag> codec_;
  FactoryCodec facade_;
  static TrackedCodec &self(void *context) {
    return *static_cast<TrackedCodec *>(context);
  }
  static UC::EventItem *create(void *context) {
    auto item = std::make_unique<TrackedItem<T, Tag>>(self(context).origins_);
    return item->origin ? item.release() : nullptr;
  }
  static UC::EventItem *clone(void *context, const UC::Event &header) {
    auto &s = self(context);
    auto *value = static_cast<const T *>(s.origins_.typed(&header, Kind));
    if (!value)
      return nullptr;
    std::unique_ptr<UC::EventItem> result(create(context));
    if (!result)
      return nullptr;
    auto *typed = dynamic_cast<TypedEventItem<T> *>(result.get());
    typed->value = *value;
    return result.release();
  }
  static bool write(void *context, UC::BufferWriter &writer,
                    const UC::Event &header) {
    auto &s = self(context);
    auto *value = static_cast<const T *>(s.origins_.typed(&header, Kind));
    if (!value)
      return false;
    s.codec_.bind(*value);
    struct Unbind {
      TypedFactoryCodec<T, Codec, Tag> &codec;
      const T &value;
      ~Unbind() { codec.unbind(value); }
    } cleanup{s.codec_, *value};
    const auto &real = s.codec_.codec();
    return real.write(real.context, writer, header);
  }
  static bool read(void *context, UC::EventItem *item,
                   UC::BufferReader &reader) {
    auto &real = self(context).codec_.codec();
    return real.read(real.context, item, reader);
  }
  static void destroy(void *, UC::EventItem *item) { delete item; }

public:
  explicit TrackedCodec(EventOrigins &origins)
      : origins_(origins), facade_{this, create, clone, write, read, destroy} {}
  void registerIn(FactoryRegistry &registry) { registry.append(Tag, &facade_); }
};
} // namespace
struct EventValueFactory::Impl {
  EventOrigins origins;
  CclFactoryRegistry registrations;
  TrackedCodec<UC::ParamValueEvent, UC::ParamValueEventClass, 20566,
               EventOrigins::Kind::Value>
      value{origins};
  TrackedCodec<UC::ParamStringEvent, UC::ParamStringEventClass, 20563,
               EventOrigins::Kind::String>
      string{origins};
  TrackedCodec<UC::ParamColorEvent, UC::ParamColorEventClass, 20547,
               EventOrigins::Kind::Color>
      color{origins};
  TrackedCodec<UC::ParamRangeEvent, UC::ParamRangeEventClass, 20562,
               EventOrigins::Kind::Range>
      range{origins};
  TrackedCodec<UC::ParamStringListEvent, UC::ParamStringListEventClass, 20556,
               EventOrigins::Kind::StringList>
      list{origins};
  TrackedCodec<UC::MeterEvent8, UC::MeterEventClass<UC::MeterEvent8, 19778>,
               19778, EventOrigins::Kind::Meter8>
      meter8{origins};
  TrackedCodec<UC::MeterEvent16, UC::MeterEventClass<UC::MeterEvent16, 19795>,
               19795, EventOrigins::Kind::Meter16>
      meter16{origins};
  UC::EventFactory factory{registrations.registry()};
  Impl() {
    auto &r = registrations.registry();
    value.registerIn(r);
    string.registerIn(r);
    color.registerIn(r);
    range.registerIn(r);
    list.registerIn(r);
    meter8.registerIn(r);
    meter16.registerIn(r);
  }
};
EventValueFactory::EventValueFactory() : impl_(std::make_unique<Impl>()) {}
EventValueFactory::~EventValueFactory() = default;
EventOrigins &EventValueFactory::origins() { return impl_->origins; }
UC::EventFactory &EventValueFactory::factory() { return impl_->factory; }
EventValueFactory::Item EventValueFactory::createType(int tag) {
  return Item(impl_->factory.createType(tag));
}
EventValueFactory::Item EventValueFactory::clone(const UC::Event &header) {
  return Item(impl_->factory.create(header));
}
EventValueFactory::Item EventValueFactory::read(const char *data, int size) {
  return Item(impl_->factory.read(data, size));
}
int EventValueFactory::write(char *data, int capacity,
                             const UC::Event &header) {
  if (!impl_->origins.param(&header) && !impl_->origins.meter(&header))
    return -1;
  return impl_->factory.write(data, capacity, header);
}
} // namespace presonus::uc
