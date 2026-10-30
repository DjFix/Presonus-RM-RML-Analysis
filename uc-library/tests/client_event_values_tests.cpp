#include "presonus/uc/ccl_bindings.hpp"
#include "presonus/uc/client_event_values.hpp"
#include <array>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <type_traits>
using namespace Presonus::UC;
using namespace presonus::uc;
void require(bool b, const char *m) {
  if (!b)
    throw std::runtime_error(m);
}
extern "C" int __wrap_socket(int, int, int) { std::abort(); }
extern "C" int __wrap_connect(int, const void *, unsigned) { std::abort(); }
extern "C" int __wrap_getaddrinfo(const char *, const char *, const void *,
                                  void *) {
  std::abort();
}
extern "C" int __wrap_getifaddrs(void *) { std::abort(); }
struct Receiver {
  unsigned paramCalls = 0, meterCalls = 0;
  void receiveEvent(const ParamEvent &view) {
    std::visit(
        [&](auto *value) {
          require(&view.header == &value->header &&
                      &view.path == &value->path &&
                      &view.index == &value->index,
                  "parameter view copied or changed field identity");
        },
        view.payload);
    ++paramCalls;
  }
  void updateLevels(const MeterEvent &view) {
    std::visit(
        [&](auto *value) {
          require(&view.header == &value->header &&
                      &view.keyBits == &value->keyBits &&
                      &view.records == &value->records &&
                      view.data == value->data.data() &&
                      view.dataCapacity == value->data.size() &&
                      view.sampleWidth == value->sampleWidth,
                  "meter view copied or changed field/sample identity");
        },
        view.payload);
    ++meterCalls;
  }
};
template <class T> void fill(T &value, unsigned variant) {
  value.header.routeA = 0x4321;
  value.header.routeB = 0xabcd;
  if constexpr (std::is_same_v<T, MeterEvent8> ||
                std::is_same_v<T, MeterEvent16>) {
    value.keyBits = 0x80fedcba;
    value.source = 65535;
    value.count = variant ? 1024 : 1;
    value.recordCount = variant ? 36 : 1;
    for (unsigned i = 0; i < 36; ++i)
      value.records[i] = {static_cast<unsigned short>(i),
                          static_cast<unsigned short>(65535 - i),
                          static_cast<unsigned short>(i * 257)};
    for (unsigned i = 0; i < value.data.size(); ++i)
      value.data[i] = static_cast<unsigned char>(i * 17 + variant);
  } else {
    std::strcpy(value.path.data(), variant ? "/prefix/longer" : "/x");
    value.index = 65535;
    if constexpr (std::is_same_v<T, ParamValueEvent>)
      value.valueBits = 0x7f812345;
    if constexpr (std::is_same_v<T, ParamColorEvent>)
      value.colorBits = 0xfedcba98;
    if constexpr (std::is_same_v<T, ParamStringEvent> ||
                  std::is_same_v<T, ParamStringListEvent>) {
      std::strcpy(value.text.data(), variant ? "opaque-text-extended" : "x");
      if constexpr (std::is_same_v<T, ParamStringListEvent>)
        value.listFieldBits = 0x89abcdef;
    }
    if constexpr (std::is_same_v<T, ParamRangeEvent>) {
      value.wordBits = {0x7f812345, 0x80000000, 0xffffffff, 0, 0x12345678};
      std::strcpy(value.labels[0].data(), "a");
      std::strcpy(value.labels[1].data(), "b");
    }
  }
}
template <class T> void checkParam(const T &value, const ParamEvent &view) {
  require(&view.header == &value.header && &view.path == &value.path &&
              &view.index == &value.index,
          "parameter prefix not borrowed");
  auto *stored = std::get_if<const T *>(&view.payload);
  require(stored && *stored == &value, "parameter payload identity lost");
}
int main() {
  try {
    static_assert(std::is_const_v<std::remove_reference_t<
                      decltype(std::declval<ParamEvent>().path)>>);
    static_assert(std::is_const_v<std::remove_reference_t<
                      decltype(std::declval<MeterEvent>().records)>>);
    EventValueFactory factory;
    Receiver receiver;
    unsigned roundtrips = 0, clones = 0, directDeletes = 0, readFailures = 0;
    for (int tag : {20566, 20563, 20547, 20562, 20556, 19778, 19795})
      for (unsigned variant = 0; variant < 2; ++variant) {
        auto item = factory.createType(tag);
        require(bool(item), "actual factory createType failed");
        Event *header = &item->getData();
        require(factory.origins().count() == 1, "create origin missing");
#define FILL(T)                                                                \
  if (auto *typed = dynamic_cast<TypedEventItem<T> *>(item.get()))             \
  fill(typed->value, variant)
        FILL(ParamValueEvent);
        FILL(ParamStringEvent);
        FILL(ParamColorEvent);
        FILL(ParamRangeEvent);
        FILL(ParamStringListEvent);
        FILL(MeterEvent8);
        FILL(MeterEvent16);
#undef FILL
        if (auto view = factory.origins().param(header))
          receiver.receiveEvent(*view);
        else {
          auto meter = factory.origins().meter(header);
          require(bool(meter), "known meter view missing");
          receiver.updateLevels(*meter);
        }
        std::array<char, 8192> wire{}, again{};
        const int size = factory.write(wire.data(), wire.size(), *header);
        require(size > 0, "actual factory write failed");
        auto copy = factory.clone(*header);
        require(bool(copy) && &copy->getData() != header,
                "clone did not create independent owned value");
        const int copySize =
            factory.write(again.data(), again.size(), copy->getData());
        require(copySize == size &&
                    std::memcmp(wire.data(), again.data(), size) == 0,
                "actual factory clone/wire value differs");
        copy.reset();
        ++clones;
        auto decoded = factory.read(wire.data(), size);
        require(bool(decoded), "actual factory wire read failed");
        const int second =
            factory.write(again.data(), again.size(), decoded->getData());
        require(second == size &&
                    std::memcmp(wire.data(), again.data(), size) == 0,
                "codec/factory/view roundtrip bytes differ");
        if (auto view = factory.origins().param(&decoded->getData()))
          receiver.receiveEvent(*view);
        else
          receiver.updateLevels(*factory.origins().meter(&decoded->getData()));
        decoded.reset();
        item.reset();
        require(factory.origins().count() == 0,
                "item destructor left stale origin");
        require(!factory.origins().param(header) &&
                    !factory.origins().meter(header),
                "dead header address remained bound");
        ++roundtrips;
        // Real EventFactory raw ownership, with ordinary virtual delete rather
        // than a special wrapper deleter, must invalidate the registry
        // automatically.
        auto *raw = factory.factory().createType(tag);
        require(raw && factory.origins().count() == 1,
                "raw actual factory create not bound");
        auto *old = &raw->getData();
        delete raw;
        require(factory.origins().count() == 0 &&
                    !factory.origins().param(old) &&
                    !factory.origins().meter(old),
                "direct virtual delete did not remove origin");
        ++directDeletes;
        // Known tag with missing body: the actual source factory owns failure
        // policy.
        const auto before = factory.origins().count();
        auto partial = factory.read(wire.data(), 2);
        if (!partial)
          ++readFailures;
        partial.reset();
        require(factory.origins().count() == before,
                "actual read cleanup leaked provenance");
      }
    ParamValueEvent external;
    external.header.type = 20566;
    external.index = 3;
    std::strcpy(external.path.data(), "/external");
    external.valueBits = 0x7fc12345;
    auto binding = factory.origins().bind(external);
    require(bool(binding), "typed overload failed");
    auto param = factory.origins().param(&external.header);
    require(bool(param), "typed origin missing");
    checkParam(external, *param);
    external.index = 99;
    external.valueBits = 0xff812345;
    require(param->index == 99 &&
                std::get<const ParamValueEvent *>(param->payload)->valueBits ==
                    0xff812345,
            "view copied payload/prefix");
    auto duplicate = factory.origins().bind(external);
    require(!duplicate, "duplicate origin silently replaced binding");
    auto moved = std::move(binding);
    binding.reset();
    require(bool(moved) && bool(factory.origins().param(&external.header)),
            "moved-from binding erased live origin");
    external.header.type = 20563;
    require(!factory.origins().param(&external.header),
            "mismatched tag accepted trusted pointer as another type");
    std::array<char, 64> buffer{};
    require(factory.write(buffer.data(), buffer.size(), external.header) == -1,
            "mismatched origin write accepted");
    external.header.type = 20566;
    moved.reset();
    require(!factory.origins().param(&external.header),
            "explicit binding release ignored");
    Event forged{20566, 0, 0, 0};
    require(!factory.origins().param(&forged) &&
                factory.write(buffer.data(), buffer.size(), forged) == -1,
            "tag alone was treated as origin proof");
    external.header.type = 20563;
    auto bad = factory.origins().bind(external);
    require(!bad, "typed/tag mismatch bind accepted");
    struct WrongItem : EventItem {
      Event header{20566, 0, 0, 0};
      Event &getData() override { return header; }
    } wrong;
    require(!factory.origins().bindItem(wrong),
            "unsupported item accepted by tag");
    struct BadHeader : TypedEventItem<ParamValueEvent> {
      Event other{20566, 0, 0, 0};
      Event &getData() override { return other; }
    } badHeader;
    badHeader.value.header.type = 20566;
    require(!factory.origins().bindItem(badHeader),
            "item/header identity mismatch accepted");
    // Independent actual TypedFactoryCodec creation/read also supplies provable
    // item identity. Caller-scoped binding is released before that item dies.
    CclFactoryRegistry registry;
    ParamValueFactoryCodec codec;
    codec.registerIn(registry.registry());
    EventFactory real(registry.registry());
    std::unique_ptr<EventItem> plain(real.createType(20566));
    auto proven = factory.origins().bindItem(*plain);
    require(bool(proven) && bool(factory.origins().param(&plain->getData())),
            "actual TypedFactoryCodec item origin not recognized");
    proven.reset();
    plain.reset();
    require(!factory.createType(123) && !factory.read("xx", 2),
            "unsupported factory tag accepted");
    EventValueFactory::Item survivor;
    {
      EventValueFactory shorter;
      survivor = shorter.createType(19795);
      require(bool(survivor), "survivor create failed");
    }
    survivor.reset();
    require(factory.origins().count() == 0, "final provenance entries leaked");
    require(readFailures > 0,
            "actual factory failure cleanup path not observed");
    std::cout << "PASS factory_roundtrips=" << roundtrips
              << " explicit_clones=" << clones
              << " direct_virtual_deletes=" << directDeletes
              << " param_callbacks=" << receiver.paramCalls
              << " meter_callbacks=" << receiver.meterCalls
              << " actual_read_failures=" << readFailures
              << " typed_factory_origin=true no_tag_only_cast=true "
                 "payload_identity_const=true automatic_lifetime=true "
                 "invalid_origins_rejected=true\n";
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
