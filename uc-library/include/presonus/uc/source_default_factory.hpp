#pragma once
#include "presonus/uc/file_control_events.hpp"
#include "presonus/uc/file_data_events.hpp"
#include "presonus/uc/meter_events.hpp"
#include "presonus/uc/misc_events.hpp"
#include "presonus/uc/no_member_events.hpp"
#include "presonus/uc/owned_data_factory_codec.hpp"
#include "presonus/uc/parameter_events.hpp"
#include "presonus/uc/typed_factory_codec.hpp"
namespace presonus::uc {
// Explicit independent inspection of the actual source-port ownership/map.
struct DefaultFactorySourceAccess {
  static int count(Presonus::UC::EventFactory &);
  static FactoryRegistry &registry(Presonus::UC::EventFactory &);
  static void *owner(Presonus::UC::EventFactory &);
};
// Independent typed access to actual shared source-port providers. Construct
// a default EventFactory first; missing initialization throws. No header cast.
template <class OriginalClass> struct DefaultFactoryProvider;
template <>
struct DefaultFactoryProvider<Presonus::UC::PrimitiveEventClassNoMembers<
    Presonus::UC::NoOpEvent, 20047>> {
  using Provider = NoOpFactoryCodec;
  static Provider &get();
};
template <> struct DefaultFactoryProvider<Presonus::UC::UDPMappingEventClass> {
  using Provider = UDPMappingFactoryCodec;
  static Provider &get();
};
template <>
struct DefaultFactoryProvider<Presonus::UC::DiscoveryAliveEventClass> {
  using Provider = DiscoveryAliveFactoryCodec;
  static Provider &get();
};
template <>
struct DefaultFactoryProvider<Presonus::UC::PrimitiveEventClassNoMembers<
    Presonus::UC::DiscoveryLeaveEvent, 17484>> {
  using Provider = DiscoveryLeaveFactoryCodec;
  static Provider &get();
};
template <>
struct DefaultFactoryProvider<Presonus::UC::PrimitiveEventClassNoMembers<
    Presonus::UC::DiscoveryQueryEvent, 17489>> {
  using Provider = DiscoveryQueryFactoryCodec;
  static Provider &get();
};
template <>
struct DefaultFactoryProvider<Presonus::UC::ExtensionQueryEventClass> {
  using Provider = ExtensionQueryFactoryCodec;
  static Provider &get();
};
template <> struct DefaultFactoryProvider<Presonus::UC::ParamEditEventClass> {
  using Provider = ParamEditFactoryCodec;
  static Provider &get();
};
template <> struct DefaultFactoryProvider<Presonus::UC::ParamValueEventClass> {
  using Provider = ParamValueFactoryCodec;
  static Provider &get();
};
template <> struct DefaultFactoryProvider<Presonus::UC::ParamStringEventClass> {
  using Provider = ParamStringFactoryCodec;
  static Provider &get();
};
template <> struct DefaultFactoryProvider<Presonus::UC::ParamModeEventClass> {
  using Provider = ParamModeFactoryCodec;
  static Provider &get();
};
template <>
struct DefaultFactoryProvider<Presonus::UC::ParamIncrementEventClass> {
  using Provider = ParamIncrementFactoryCodec;
  static Provider &get();
};
template <> struct DefaultFactoryProvider<Presonus::UC::ParamColorEventClass> {
  using Provider = ParamColorFactoryCodec;
  static Provider &get();
};
template <> struct DefaultFactoryProvider<Presonus::UC::ParamRangeEventClass> {
  using Provider = ParamRangeFactoryCodec;
  static Provider &get();
};
template <>
struct DefaultFactoryProvider<Presonus::UC::ParamStringListEventClass> {
  using Provider = ParamStringListFactoryCodec;
  static Provider &get();
};
template <>
struct DefaultFactoryProvider<
    Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent8, 19778>> {
  using Provider = Meter8FactoryCodec;
  static Provider &get();
};
template <>
struct DefaultFactoryProvider<
    Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent16, 19795>> {
  using Provider = Meter16FactoryCodec;
  static Provider &get();
};
template <> struct DefaultFactoryProvider<Presonus::UC::TimeCodeEventClass> {
  using Provider = TimeCodeFactoryCodec;
  static Provider &get();
};
template <> struct DefaultFactoryProvider<Presonus::UC::MusicInputEventClass> {
  using Provider = MusicInputFactoryCodec;
  static Provider &get();
};
template <>
struct DefaultFactoryProvider<Presonus::UC::PrimitiveEventClassNoMembers<
    Presonus::UC::KeepAliveEvent, 19265>> {
  using Provider = KeepAliveFactoryCodec;
  static Provider &get();
};
template <> struct DefaultFactoryProvider<Presonus::UC::FileRequestEventClass> {
  using Provider = FileRequestFactoryCodec;
  static Provider &get();
};
template <> struct DefaultFactoryProvider<Presonus::UC::FileDataEventClass> {
  using Provider = FileDataFactoryCodec;
  static Provider &get();
};
template <>
struct DefaultFactoryProvider<Presonus::UC::FileDataRateEventClass> {
  using Provider = FileDataRateFactoryCodec;
  static Provider &get();
};
template <> struct DefaultFactoryProvider<Presonus::UC::FileAbortEventClass> {
  using Provider = FileAbortFactoryCodec;
  static Provider &get();
};
template <> struct DefaultFactoryProvider<Presonus::UC::BinaryEventClass> {
  using Provider = BinaryFactoryCodec;
  static Provider &get();
};
template <>
struct DefaultFactoryProvider<Presonus::UC::DataEventClass<
    Presonus::UC::EncodedMessageEvent<19021>, 19021>> {
  using Provider = EncodedDataFactoryCodec<19021>;
  static Provider &get();
};
template <>
struct DefaultFactoryProvider<Presonus::UC::DataEventClass<
    Presonus::UC::EncodedMessageEvent<23117>, 23117>> {
  using Provider = EncodedDataFactoryCodec<23117>;
  static Provider &get();
};
template <>
struct DefaultFactoryProvider<Presonus::UC::DataEventClass<
    Presonus::UC::EncodedMessageEvent<21826>, 21826>> {
  using Provider = EncodedDataFactoryCodec<21826>;
  static Provider &get();
};
template <>
struct DefaultFactoryProvider<Presonus::UC::DataEventClass<
    Presonus::UC::EncodedMessageEvent<23106>, 23106>> {
  using Provider = EncodedDataFactoryCodec<23106>;
  static Provider &get();
};
template <>
struct DefaultFactoryProvider<Presonus::UC::MessageChunkEventClass> {
  using Provider = MessageChunkFactoryCodec;
  static Provider &get();
};
template <>
struct DefaultFactoryProvider<
    Presonus::UC::DataEventClass<Presonus::UC::LoopbackQueryEvent, 19537>> {
  using Provider = LoopbackQueryDataFactoryCodec;
  static Provider &get();
};
template <>
struct DefaultFactoryProvider<
    Presonus::UC::DataEventClass<Presonus::UC::LoopbackReplyEvent, 19538>> {
  using Provider = LoopbackReplyDataFactoryCodec;
  static Provider &get();
};
template <> struct DefaultFactoryProvider<Presonus::UC::DebugEventClass> {
  using Provider = DebugFactoryCodec;
  static Provider &get();
};
template <> struct DefaultFactoryProvider<Presonus::UC::MidiMessageEventClass> {
  using Provider = MidiMessageFactoryCodec;
  static Provider &get();
};
template <>
struct DefaultFactoryProvider<Presonus::UC::MidiShortSysexEventClass> {
  using Provider = MidiShortSysexFactoryCodec;
  static Provider &get();
};
template <>
struct DefaultFactoryProvider<
    Presonus::UC::DataEventClass<Presonus::UC::MidiLongSysexEvent, 21324>> {
  using Provider = MidiLongSysexDataFactoryCodec;
  static Provider &get();
};
} // namespace presonus::uc
