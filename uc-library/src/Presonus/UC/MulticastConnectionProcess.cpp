#include "core/system/coretime.h"
#include "presonus/uc/MulticastDatagramProvider.hpp"
#include "presonus/uc/basic_connection_runtime.hpp"
#include "presonus/uc/source_default_factory.hpp"
#include <memory>
#include <optional>
namespace Presonus::UC {
namespace {
template <class> struct BoundValue;
template <class Codec, class Value>
struct BoundValue<void (Codec::*)(const Value &)> {
  using Type = Value;
};
template <class OriginalClass, class Action>
std::optional<bool> withQueuedValue(EventItem &item, Action action) {
  using Provider =
      typename presonus::uc::DefaultFactoryProvider<OriginalClass>::Provider;
  using Value = typename BoundValue<decltype(&Provider::bind)>::Type;
  Value *value = nullptr;
  if (auto *typed = dynamic_cast<presonus::uc::TypedEventItem<Value> *>(&item))
    value = &typed->value;
  else if (auto *owned =
               dynamic_cast<presonus::uc::OwnedCodecItem<Value> *>(&item))
    value = &owned->value;
  if (!value)
    return std::nullopt;
  auto &provider = presonus::uc::DefaultFactoryProvider<OriginalClass>::get();
  provider.bind(*value);
  struct Unbind {
    Provider &provider;
    Value &value;
    ~Unbind() { provider.unbind(value); }
  } unbind{provider, *value};
  return action(item.getData());
}
} // namespace
void MulticastConnection::process(bool outgoingOnly) {
  if (state_.resetMarker) {
    state_.resetMarker = 0;
    NoOpEvent noop{{20047, 16, 0, 0}};
    presonus::uc::NoOpFactoryCodec *codec = nullptr;
    if (state_.outgoing.factory &&
        presonus::uc::DefaultFactorySourceAccess::owner(
            *state_.outgoing.factory))
      codec = &presonus::uc::DefaultFactoryProvider<
          PrimitiveEventClassNoMembers<NoOpEvent, 20047>>::get();
    if (codec)
      codec->bind(noop);
    struct Unbind {
      presonus::uc::NoOpFactoryCodec *codec;
      NoOpEvent &value;
      ~Unbind() {
        if (codec)
          codec->unbind(value);
      }
    } unbind{codec, noop};
    sendEvent(noop.header);
  }
  const bool changed = state_.adapterState.changed != 0;
  auto *queue = state_.outgoing.queue;
  if (!queue)
    throw std::logic_error("Actual outgoing EventQueue provider is required");
  presonus::uc::MulticastDatagramProvider provider(*this);
  while (std::unique_ptr<EventItem> item{queue->retrieveEvent()}) {
    auto send = [&](const Event &event) {
      return provider.sendTo(state_.broadcast, event);
    };
    std::optional<bool> sent;
    // Every actual default-factory typed/owned payload gets an explicit live
    // binding; unknown custom providers retain their own provenance contract.
    if (state_.outgoing.factory &&
        presonus::uc::DefaultFactorySourceAccess::owner(
            *state_.outgoing.factory)) {
      if (!sent)
        sent = withQueuedValue<Presonus::UC::PrimitiveEventClassNoMembers<
            Presonus::UC::NoOpEvent, 20047>>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::UDPMappingEventClass>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::DiscoveryAliveEventClass>(*item,
                                                                       send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::PrimitiveEventClassNoMembers<
            Presonus::UC::DiscoveryLeaveEvent, 17484>>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::PrimitiveEventClassNoMembers<
            Presonus::UC::DiscoveryQueryEvent, 17489>>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::ExtensionQueryEventClass>(*item,
                                                                       send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::ParamEditEventClass>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::ParamValueEventClass>(*item, send);
      if (!sent)
        sent =
            withQueuedValue<Presonus::UC::ParamStringEventClass>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::ParamModeEventClass>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::ParamIncrementEventClass>(*item,
                                                                       send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::ParamColorEventClass>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::ParamRangeEventClass>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::ParamStringListEventClass>(*item,
                                                                        send);
      if (!sent)
        sent = withQueuedValue<
            Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent8, 19778>>(
            *item, send);
      if (!sent)
        sent = withQueuedValue<
            Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent16, 19795>>(
            *item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::TimeCodeEventClass>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::MusicInputEventClass>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::PrimitiveEventClassNoMembers<
            Presonus::UC::KeepAliveEvent, 19265>>(*item, send);
      if (!sent)
        sent =
            withQueuedValue<Presonus::UC::FileRequestEventClass>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::FileDataEventClass>(*item, send);
      if (!sent)
        sent =
            withQueuedValue<Presonus::UC::FileDataRateEventClass>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::FileAbortEventClass>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::BinaryEventClass>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::DataEventClass<
            Presonus::UC::EncodedMessageEvent<19021>, 19021>>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::DataEventClass<
            Presonus::UC::EncodedMessageEvent<23117>, 23117>>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::DataEventClass<
            Presonus::UC::EncodedMessageEvent<21826>, 21826>>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::DataEventClass<
            Presonus::UC::EncodedMessageEvent<23106>, 23106>>(*item, send);
      if (!sent)
        sent =
            withQueuedValue<Presonus::UC::MessageChunkEventClass>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::DataEventClass<
            Presonus::UC::LoopbackQueryEvent, 19537>>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::DataEventClass<
            Presonus::UC::LoopbackReplyEvent, 19538>>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::DebugEventClass>(*item, send);
      if (!sent)
        sent =
            withQueuedValue<Presonus::UC::MidiMessageEventClass>(*item, send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::MidiShortSysexEventClass>(*item,
                                                                       send);
      if (!sent)
        sent = withQueuedValue<Presonus::UC::DataEventClass<
            Presonus::UC::MidiLongSysexEvent, 21324>>(*item, send);
    }
    if (!sent)
      sent = send(item->getData());
    if (!*sent)
      break;
  }
  if (outgoingOnly)
    return;
  auto drain = [&](presonus::uc::SocketBundleState &bundle) {
    for (int i = 0; i < bundle.count; ++i) {
      auto &socket = *bundle.sockets[i];
      while (socket.isReadable(1))
        if (!provider.readEvent(socket))
          break;
    }
  };
  if (state_.multicastEnabled) {
    if (state_.groupPending && !changed) {
      const auto now =
          Core::SystemClock::getTime() /
          static_cast<std::int64_t>(Core::SystemClock::getFrequency() / 1000);
      if (now - state_.pendingSinceMilliseconds > 9999) {
        state_.pendingSinceMilliseconds = now;
        for (int i = 0; i < state_.multicastStorage.count; ++i) {
          presonus::uc::AdapterIPAddress any;
          if (state_.multicastStorage.sockets[i]->joinMulticastGroup(
                  state_.group, any))
            setMulticastGroupPending(false);
        }
      }
    }
    drain(state_.multicastStorage);
    if (state_.multicast.isAnyError(1) || changed) {
      makeMulticastSockets(false);
      makeMulticastSockets(true);
    }
  }
  if (state_.unicastEnabled) {
    drain(state_.unicastStorage);
    if (state_.unicast.isAnyError(1) || changed) {
      makeUnicastSockets(false);
      makeUnicastSockets(true);
    }
  }
}
} // namespace Presonus::UC
