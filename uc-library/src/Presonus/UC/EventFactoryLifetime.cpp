#include "presonus/uc/ccl_bindings.hpp"
#include "presonus/uc/file_control_events.hpp"
#include "presonus/uc/file_data_events.hpp"
#include "presonus/uc/meter_events.hpp"
#include "presonus/uc/misc_events.hpp"
#include "presonus/uc/no_member_events.hpp"
#include "presonus/uc/owned_data_factory_codec.hpp"
#include "presonus/uc/parameter_events.hpp"
#include "presonus/uc/source_default_factory.hpp"
#include "presonus/uc/typed_factory_codec.hpp"
namespace {
template <class OriginalClass> struct SourceCodec;
template <>
struct SourceCodec<Presonus::UC::PrimitiveEventClassNoMembers<
    Presonus::UC::NoOpEvent, 20047>> {
  using Provider = presonus::uc::NoOpFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 20047;
};
template <> struct SourceCodec<Presonus::UC::UDPMappingEventClass> {
  using Provider = presonus::uc::UDPMappingFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 21837;
};
template <> struct SourceCodec<Presonus::UC::DiscoveryAliveEventClass> {
  using Provider = presonus::uc::DiscoveryAliveFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 17473;
};
template <>
struct SourceCodec<Presonus::UC::PrimitiveEventClassNoMembers<
    Presonus::UC::DiscoveryLeaveEvent, 17484>> {
  using Provider = presonus::uc::DiscoveryLeaveFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 17484;
};
template <>
struct SourceCodec<Presonus::UC::PrimitiveEventClassNoMembers<
    Presonus::UC::DiscoveryQueryEvent, 17489>> {
  using Provider = presonus::uc::DiscoveryQueryFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 17489;
};
template <> struct SourceCodec<Presonus::UC::ExtensionQueryEventClass> {
  using Provider = presonus::uc::ExtensionQueryFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 17745;
};
template <> struct SourceCodec<Presonus::UC::ParamEditEventClass> {
  using Provider = presonus::uc::ParamEditFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 20549;
};
template <> struct SourceCodec<Presonus::UC::ParamValueEventClass> {
  using Provider = presonus::uc::ParamValueFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 20566;
};
template <> struct SourceCodec<Presonus::UC::ParamStringEventClass> {
  using Provider = presonus::uc::ParamStringFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 20563;
};
template <> struct SourceCodec<Presonus::UC::ParamModeEventClass> {
  using Provider = presonus::uc::ParamModeFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 20557;
};
template <> struct SourceCodec<Presonus::UC::ParamIncrementEventClass> {
  using Provider = presonus::uc::ParamIncrementFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 20553;
};
template <> struct SourceCodec<Presonus::UC::ParamColorEventClass> {
  using Provider = presonus::uc::ParamColorFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 20547;
};
template <> struct SourceCodec<Presonus::UC::ParamRangeEventClass> {
  using Provider = presonus::uc::ParamRangeFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 20562;
};
template <> struct SourceCodec<Presonus::UC::ParamStringListEventClass> {
  using Provider = presonus::uc::ParamStringListFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 20556;
};
template <>
struct SourceCodec<
    Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent8, 19778>> {
  using Provider = presonus::uc::Meter8FactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 19778;
};
template <>
struct SourceCodec<
    Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent16, 19795>> {
  using Provider = presonus::uc::Meter16FactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 19795;
};
template <> struct SourceCodec<Presonus::UC::TimeCodeEventClass> {
  using Provider = presonus::uc::TimeCodeFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 21571;
};
template <> struct SourceCodec<Presonus::UC::MusicInputEventClass> {
  using Provider = presonus::uc::MusicInputFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 19785;
};
template <>
struct SourceCodec<Presonus::UC::PrimitiveEventClassNoMembers<
    Presonus::UC::KeepAliveEvent, 19265>> {
  using Provider = presonus::uc::KeepAliveFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 19265;
};
template <> struct SourceCodec<Presonus::UC::FileRequestEventClass> {
  using Provider = presonus::uc::FileRequestFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 18002;
};
template <> struct SourceCodec<Presonus::UC::FileDataEventClass> {
  using Provider = presonus::uc::FileDataFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 17988;
};
template <> struct SourceCodec<Presonus::UC::FileDataRateEventClass> {
  using Provider = presonus::uc::FileDataRateFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 18003;
};
template <> struct SourceCodec<Presonus::UC::FileAbortEventClass> {
  using Provider = presonus::uc::FileAbortFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 17985;
};
template <> struct SourceCodec<Presonus::UC::BinaryEventClass> {
  using Provider = presonus::uc::BinaryFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 16975;
};
template <>
struct SourceCodec<Presonus::UC::DataEventClass<
    Presonus::UC::EncodedMessageEvent<19021>, 19021>> {
  using Provider = presonus::uc::EncodedDataFactoryCodec<19021>;
  inline static Provider *instance = nullptr;
  static constexpr int type = 19021;
};
template <>
struct SourceCodec<Presonus::UC::DataEventClass<
    Presonus::UC::EncodedMessageEvent<23117>, 23117>> {
  using Provider = presonus::uc::EncodedDataFactoryCodec<23117>;
  inline static Provider *instance = nullptr;
  static constexpr int type = 23117;
};
template <>
struct SourceCodec<Presonus::UC::DataEventClass<
    Presonus::UC::EncodedMessageEvent<21826>, 21826>> {
  using Provider = presonus::uc::EncodedDataFactoryCodec<21826>;
  inline static Provider *instance = nullptr;
  static constexpr int type = 21826;
};
template <>
struct SourceCodec<Presonus::UC::DataEventClass<
    Presonus::UC::EncodedMessageEvent<23106>, 23106>> {
  using Provider = presonus::uc::EncodedDataFactoryCodec<23106>;
  inline static Provider *instance = nullptr;
  static constexpr int type = 23106;
};
template <> struct SourceCodec<Presonus::UC::MessageChunkEventClass> {
  using Provider = presonus::uc::MessageChunkFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 17227;
};
template <>
struct SourceCodec<
    Presonus::UC::DataEventClass<Presonus::UC::LoopbackQueryEvent, 19537>> {
  using Provider = presonus::uc::LoopbackQueryDataFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 19537;
};
template <>
struct SourceCodec<
    Presonus::UC::DataEventClass<Presonus::UC::LoopbackReplyEvent, 19538>> {
  using Provider = presonus::uc::LoopbackReplyDataFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 19538;
};
template <> struct SourceCodec<Presonus::UC::DebugEventClass> {
  using Provider = presonus::uc::DebugFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 17474;
};
template <> struct SourceCodec<Presonus::UC::MidiMessageEventClass> {
  using Provider = presonus::uc::MidiMessageFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 19789;
};
template <> struct SourceCodec<Presonus::UC::MidiShortSysexEventClass> {
  using Provider = presonus::uc::MidiShortSysexFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 21331;
};
template <>
struct SourceCodec<
    Presonus::UC::DataEventClass<Presonus::UC::MidiLongSysexEvent, 21324>> {
  using Provider = presonus::uc::MidiLongSysexDataFactoryCodec;
  inline static Provider *instance = nullptr;
  static constexpr int type = 21324;
};
} // namespace
namespace Presonus::UC {
// Per-instance real CCL map; original pool/class layout is intentionally not
// represented. Shared local statics below own actual concrete provider state.
struct EventFactory::SourceOwned {
  Core::HashMap<int, const presonus::uc::FactoryCodec *> entries;
  presonus::uc::FactoryRegistry registry;
  static int hash(const int &key, int modulus) {
    const int raw = EventFactory::hashEventType(key, modulus);
    return raw < 0 ? raw + modulus : raw;
  }
  SourceOwned() : entries(32, hash, nullptr) {
    registry.modulus = 32;
    registry.sourceBackendContext = &entries;
    registry.sourceBackendGet =
        [](void *p, const presonus::uc::FactoryCodec *&out, int key) {
          return static_cast<decltype(entries) *>(p)->get(out, key);
        };
    registry.sourceBackendAppend = [](void *p, int key,
                                      const presonus::uc::FactoryCodec *codec) {
      static_cast<decltype(entries) *>(p)->add(key, codec);
    };
  }
};
EventFactory::EventFactory(presonus::uc::FactoryRegistry &registry)
    : registry_(registry) {}
EventFactory::~EventFactory() = default;
template <class T> void EventFactory::addClass() {
  static typename SourceCodec<T>::Provider theInstance;
  SourceCodec<T>::instance = &theInstance;
  registry_.append(SourceCodec<T>::type, &theInstance.codec());
}
EventFactory::EventFactory()
    : owned_(std::make_unique<SourceOwned>()), registry_(owned_->registry) {
  addClass<Presonus::UC::PrimitiveEventClassNoMembers<Presonus::UC::NoOpEvent,
                                                      20047>>();
  addClass<Presonus::UC::UDPMappingEventClass>();
  addClass<Presonus::UC::DiscoveryAliveEventClass>();
  addClass<Presonus::UC::PrimitiveEventClassNoMembers<
      Presonus::UC::DiscoveryLeaveEvent, 17484>>();
  addClass<Presonus::UC::PrimitiveEventClassNoMembers<
      Presonus::UC::DiscoveryQueryEvent, 17489>>();
  addClass<Presonus::UC::ExtensionQueryEventClass>();
  addClass<Presonus::UC::ParamEditEventClass>();
  addClass<Presonus::UC::ParamValueEventClass>();
  addClass<Presonus::UC::ParamStringEventClass>();
  addClass<Presonus::UC::ParamModeEventClass>();
  addClass<Presonus::UC::ParamIncrementEventClass>();
  addClass<Presonus::UC::ParamColorEventClass>();
  addClass<Presonus::UC::ParamRangeEventClass>();
  addClass<Presonus::UC::ParamStringListEventClass>();
  addClass<Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent8, 19778>>();
  addClass<Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent16, 19795>>();
  addClass<Presonus::UC::TimeCodeEventClass>();
  addClass<Presonus::UC::MusicInputEventClass>();
  addClass<Presonus::UC::PrimitiveEventClassNoMembers<
      Presonus::UC::KeepAliveEvent, 19265>>();
  addClass<Presonus::UC::FileRequestEventClass>();
  addClass<Presonus::UC::FileDataEventClass>();
  addClass<Presonus::UC::FileDataRateEventClass>();
  addClass<Presonus::UC::FileAbortEventClass>();
  addClass<Presonus::UC::BinaryEventClass>();
  addClass<Presonus::UC::DataEventClass<
      Presonus::UC::EncodedMessageEvent<19021>, 19021>>();
  addClass<Presonus::UC::DataEventClass<
      Presonus::UC::EncodedMessageEvent<23117>, 23117>>();
  addClass<Presonus::UC::DataEventClass<
      Presonus::UC::EncodedMessageEvent<21826>, 21826>>();
  addClass<Presonus::UC::DataEventClass<
      Presonus::UC::EncodedMessageEvent<23106>, 23106>>();
  addClass<Presonus::UC::MessageChunkEventClass>();
  addClass<
      Presonus::UC::DataEventClass<Presonus::UC::LoopbackQueryEvent, 19537>>();
  addClass<
      Presonus::UC::DataEventClass<Presonus::UC::LoopbackReplyEvent, 19538>>();
  addClass<Presonus::UC::DebugEventClass>();
  addClass<Presonus::UC::MidiMessageEventClass>();
  addClass<Presonus::UC::MidiShortSysexEventClass>();
  addClass<
      Presonus::UC::DataEventClass<Presonus::UC::MidiLongSysexEvent, 21324>>();
}
template void EventFactory::addClass<Presonus::UC::PrimitiveEventClassNoMembers<
    Presonus::UC::NoOpEvent, 20047>>();
template void EventFactory::addClass<Presonus::UC::UDPMappingEventClass>();
template void EventFactory::addClass<Presonus::UC::DiscoveryAliveEventClass>();
template void EventFactory::addClass<Presonus::UC::PrimitiveEventClassNoMembers<
    Presonus::UC::DiscoveryLeaveEvent, 17484>>();
template void EventFactory::addClass<Presonus::UC::PrimitiveEventClassNoMembers<
    Presonus::UC::DiscoveryQueryEvent, 17489>>();
template void EventFactory::addClass<Presonus::UC::ExtensionQueryEventClass>();
template void EventFactory::addClass<Presonus::UC::ParamEditEventClass>();
template void EventFactory::addClass<Presonus::UC::ParamValueEventClass>();
template void EventFactory::addClass<Presonus::UC::ParamStringEventClass>();
template void EventFactory::addClass<Presonus::UC::ParamModeEventClass>();
template void EventFactory::addClass<Presonus::UC::ParamIncrementEventClass>();
template void EventFactory::addClass<Presonus::UC::ParamColorEventClass>();
template void EventFactory::addClass<Presonus::UC::ParamRangeEventClass>();
template void EventFactory::addClass<Presonus::UC::ParamStringListEventClass>();
template void EventFactory::addClass<
    Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent8, 19778>>();
template void EventFactory::addClass<
    Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent16, 19795>>();
template void EventFactory::addClass<Presonus::UC::TimeCodeEventClass>();
template void EventFactory::addClass<Presonus::UC::MusicInputEventClass>();
template void EventFactory::addClass<Presonus::UC::PrimitiveEventClassNoMembers<
    Presonus::UC::KeepAliveEvent, 19265>>();
template void EventFactory::addClass<Presonus::UC::FileRequestEventClass>();
template void EventFactory::addClass<Presonus::UC::FileDataEventClass>();
template void EventFactory::addClass<Presonus::UC::FileDataRateEventClass>();
template void EventFactory::addClass<Presonus::UC::FileAbortEventClass>();
template void EventFactory::addClass<Presonus::UC::BinaryEventClass>();
template void EventFactory::addClass<Presonus::UC::DataEventClass<
    Presonus::UC::EncodedMessageEvent<19021>, 19021>>();
template void EventFactory::addClass<Presonus::UC::DataEventClass<
    Presonus::UC::EncodedMessageEvent<23117>, 23117>>();
template void EventFactory::addClass<Presonus::UC::DataEventClass<
    Presonus::UC::EncodedMessageEvent<21826>, 21826>>();
template void EventFactory::addClass<Presonus::UC::DataEventClass<
    Presonus::UC::EncodedMessageEvent<23106>, 23106>>();
template void EventFactory::addClass<Presonus::UC::MessageChunkEventClass>();
template void EventFactory::addClass<
    Presonus::UC::DataEventClass<Presonus::UC::LoopbackQueryEvent, 19537>>();
template void EventFactory::addClass<
    Presonus::UC::DataEventClass<Presonus::UC::LoopbackReplyEvent, 19538>>();
template void EventFactory::addClass<Presonus::UC::DebugEventClass>();
template void EventFactory::addClass<Presonus::UC::MidiMessageEventClass>();
template void EventFactory::addClass<Presonus::UC::MidiShortSysexEventClass>();
template void EventFactory::addClass<
    Presonus::UC::DataEventClass<Presonus::UC::MidiLongSysexEvent, 21324>>();
} // namespace Presonus::UC

namespace presonus::uc {
int DefaultFactorySourceAccess::count(Presonus::UC::EventFactory &factory) {
  return factory.owned_ ? factory.owned_->entries.count() : -1;
}
FactoryRegistry &
DefaultFactorySourceAccess::registry(Presonus::UC::EventFactory &factory) {
  return factory.registry_;
}
void *DefaultFactorySourceAccess::owner(Presonus::UC::EventFactory &factory) {
  return factory.owned_.get();
}
DefaultFactoryProvider<Presonus::UC::PrimitiveEventClassNoMembers<
    Presonus::UC::NoOpEvent, 20047>>::Provider &
DefaultFactoryProvider<Presonus::UC::PrimitiveEventClassNoMembers<
    Presonus::UC::NoOpEvent, 20047>>::get() {
  auto *provider = SourceCodec<Presonus::UC::PrimitiveEventClassNoMembers<
      Presonus::UC::NoOpEvent, 20047>>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::UDPMappingEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::UDPMappingEventClass>::get() {
  auto *provider = SourceCodec<Presonus::UC::UDPMappingEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::DiscoveryAliveEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::DiscoveryAliveEventClass>::get() {
  auto *provider =
      SourceCodec<Presonus::UC::DiscoveryAliveEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::PrimitiveEventClassNoMembers<
    Presonus::UC::DiscoveryLeaveEvent, 17484>>::Provider &
DefaultFactoryProvider<Presonus::UC::PrimitiveEventClassNoMembers<
    Presonus::UC::DiscoveryLeaveEvent, 17484>>::get() {
  auto *provider = SourceCodec<Presonus::UC::PrimitiveEventClassNoMembers<
      Presonus::UC::DiscoveryLeaveEvent, 17484>>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::PrimitiveEventClassNoMembers<
    Presonus::UC::DiscoveryQueryEvent, 17489>>::Provider &
DefaultFactoryProvider<Presonus::UC::PrimitiveEventClassNoMembers<
    Presonus::UC::DiscoveryQueryEvent, 17489>>::get() {
  auto *provider = SourceCodec<Presonus::UC::PrimitiveEventClassNoMembers<
      Presonus::UC::DiscoveryQueryEvent, 17489>>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::ExtensionQueryEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::ExtensionQueryEventClass>::get() {
  auto *provider =
      SourceCodec<Presonus::UC::ExtensionQueryEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::ParamEditEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::ParamEditEventClass>::get() {
  auto *provider = SourceCodec<Presonus::UC::ParamEditEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::ParamValueEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::ParamValueEventClass>::get() {
  auto *provider = SourceCodec<Presonus::UC::ParamValueEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::ParamStringEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::ParamStringEventClass>::get() {
  auto *provider = SourceCodec<Presonus::UC::ParamStringEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::ParamModeEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::ParamModeEventClass>::get() {
  auto *provider = SourceCodec<Presonus::UC::ParamModeEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::ParamIncrementEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::ParamIncrementEventClass>::get() {
  auto *provider =
      SourceCodec<Presonus::UC::ParamIncrementEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::ParamColorEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::ParamColorEventClass>::get() {
  auto *provider = SourceCodec<Presonus::UC::ParamColorEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::ParamRangeEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::ParamRangeEventClass>::get() {
  auto *provider = SourceCodec<Presonus::UC::ParamRangeEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::ParamStringListEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::ParamStringListEventClass>::get() {
  auto *provider =
      SourceCodec<Presonus::UC::ParamStringListEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<
    Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent8, 19778>>::Provider &
DefaultFactoryProvider<
    Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent8, 19778>>::get() {
  auto *provider =
      SourceCodec<Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent8,
                                                19778>>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent16,
                                                     19795>>::Provider &
DefaultFactoryProvider<
    Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent16, 19795>>::get() {
  auto *provider =
      SourceCodec<Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent16,
                                                19795>>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::TimeCodeEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::TimeCodeEventClass>::get() {
  auto *provider = SourceCodec<Presonus::UC::TimeCodeEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::MusicInputEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::MusicInputEventClass>::get() {
  auto *provider = SourceCodec<Presonus::UC::MusicInputEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::PrimitiveEventClassNoMembers<
    Presonus::UC::KeepAliveEvent, 19265>>::Provider &
DefaultFactoryProvider<Presonus::UC::PrimitiveEventClassNoMembers<
    Presonus::UC::KeepAliveEvent, 19265>>::get() {
  auto *provider = SourceCodec<Presonus::UC::PrimitiveEventClassNoMembers<
      Presonus::UC::KeepAliveEvent, 19265>>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::FileRequestEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::FileRequestEventClass>::get() {
  auto *provider = SourceCodec<Presonus::UC::FileRequestEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::FileDataEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::FileDataEventClass>::get() {
  auto *provider = SourceCodec<Presonus::UC::FileDataEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::FileDataRateEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::FileDataRateEventClass>::get() {
  auto *provider = SourceCodec<Presonus::UC::FileDataRateEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::FileAbortEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::FileAbortEventClass>::get() {
  auto *provider = SourceCodec<Presonus::UC::FileAbortEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::BinaryEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::BinaryEventClass>::get() {
  auto *provider = SourceCodec<Presonus::UC::BinaryEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::DataEventClass<
    Presonus::UC::EncodedMessageEvent<19021>, 19021>>::Provider &
DefaultFactoryProvider<Presonus::UC::DataEventClass<
    Presonus::UC::EncodedMessageEvent<19021>, 19021>>::get() {
  auto *provider = SourceCodec<Presonus::UC::DataEventClass<
      Presonus::UC::EncodedMessageEvent<19021>, 19021>>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::DataEventClass<
    Presonus::UC::EncodedMessageEvent<23117>, 23117>>::Provider &
DefaultFactoryProvider<Presonus::UC::DataEventClass<
    Presonus::UC::EncodedMessageEvent<23117>, 23117>>::get() {
  auto *provider = SourceCodec<Presonus::UC::DataEventClass<
      Presonus::UC::EncodedMessageEvent<23117>, 23117>>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::DataEventClass<
    Presonus::UC::EncodedMessageEvent<21826>, 21826>>::Provider &
DefaultFactoryProvider<Presonus::UC::DataEventClass<
    Presonus::UC::EncodedMessageEvent<21826>, 21826>>::get() {
  auto *provider = SourceCodec<Presonus::UC::DataEventClass<
      Presonus::UC::EncodedMessageEvent<21826>, 21826>>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::DataEventClass<
    Presonus::UC::EncodedMessageEvent<23106>, 23106>>::Provider &
DefaultFactoryProvider<Presonus::UC::DataEventClass<
    Presonus::UC::EncodedMessageEvent<23106>, 23106>>::get() {
  auto *provider = SourceCodec<Presonus::UC::DataEventClass<
      Presonus::UC::EncodedMessageEvent<23106>, 23106>>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::MessageChunkEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::MessageChunkEventClass>::get() {
  auto *provider = SourceCodec<Presonus::UC::MessageChunkEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::DataEventClass<
    Presonus::UC::LoopbackQueryEvent, 19537>>::Provider &
DefaultFactoryProvider<Presonus::UC::DataEventClass<
    Presonus::UC::LoopbackQueryEvent, 19537>>::get() {
  auto *provider =
      SourceCodec<Presonus::UC::DataEventClass<Presonus::UC::LoopbackQueryEvent,
                                               19537>>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::DataEventClass<
    Presonus::UC::LoopbackReplyEvent, 19538>>::Provider &
DefaultFactoryProvider<Presonus::UC::DataEventClass<
    Presonus::UC::LoopbackReplyEvent, 19538>>::get() {
  auto *provider =
      SourceCodec<Presonus::UC::DataEventClass<Presonus::UC::LoopbackReplyEvent,
                                               19538>>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::DebugEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::DebugEventClass>::get() {
  auto *provider = SourceCodec<Presonus::UC::DebugEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::MidiMessageEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::MidiMessageEventClass>::get() {
  auto *provider = SourceCodec<Presonus::UC::MidiMessageEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::MidiShortSysexEventClass>::Provider &
DefaultFactoryProvider<Presonus::UC::MidiShortSysexEventClass>::get() {
  auto *provider =
      SourceCodec<Presonus::UC::MidiShortSysexEventClass>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
DefaultFactoryProvider<Presonus::UC::DataEventClass<
    Presonus::UC::MidiLongSysexEvent, 21324>>::Provider &
DefaultFactoryProvider<Presonus::UC::DataEventClass<
    Presonus::UC::MidiLongSysexEvent, 21324>>::get() {
  auto *provider =
      SourceCodec<Presonus::UC::DataEventClass<Presonus::UC::MidiLongSysexEvent,
                                               21324>>::instance;
  if (!provider)
    throw std::logic_error(
        "construct a default EventFactory before requesting its provider");
  return *provider;
}
} // namespace presonus::uc
