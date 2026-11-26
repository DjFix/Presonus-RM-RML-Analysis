#include "presonus/uc/ConnectionTransportProvider.hpp"
#include "presonus/uc/basic_connection_runtime.hpp"
#include "presonus/uc/event_dispatcher.hpp"
#include "presonus/uc/network_activity_manager.hpp"
#include "presonus/uc/source_default_factory.hpp"
#include <array>
#include <cstring>
#include <memory>
#include <vector>
namespace {
template <class Provider> struct ItemType {
  using type = presonus::uc::OwnedCodecItem<typename Provider::value_type>;
};
template <class Value, class Codec, int Type>
struct ItemType<presonus::uc::TypedFactoryCodec<Value, Codec, Type>> {
  using type = presonus::uc::TypedEventItem<Value>;
};
template <class OriginalClass, class Callback>
bool bindActualItem(Presonus::UC::EventItem &item, Callback callback,
                    bool &matched) {
  using Provider =
      typename presonus::uc::DefaultFactoryProvider<OriginalClass>::Provider;
  using Item = typename ItemType<Provider>::type;
  auto *typed = dynamic_cast<Item *>(&item);
  if (!typed)
    return false;
  matched = true;
  auto &provider = presonus::uc::DefaultFactoryProvider<OriginalClass>::get();
  provider.bind(typed->value);
  struct Unbind {
    Provider &provider;
    decltype(typed) item;
    ~Unbind() { provider.unbind(item->value); }
  } unbind{provider, typed};
  return callback(item.getData());
}
template <class Callback>
bool withActualItem(Presonus::UC::EventItem &item, Callback callback) {
  bool matched = false;
  bool result = false;
  result = bindActualItem<Presonus::UC::PrimitiveEventClassNoMembers<
      Presonus::UC::NoOpEvent, 20047>>(item, callback, matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::UDPMappingEventClass>(item, callback,
                                                              matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::DiscoveryAliveEventClass>(
      item, callback, matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::PrimitiveEventClassNoMembers<
      Presonus::UC::DiscoveryLeaveEvent, 17484>>(item, callback, matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::PrimitiveEventClassNoMembers<
      Presonus::UC::DiscoveryQueryEvent, 17489>>(item, callback, matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::ExtensionQueryEventClass>(
      item, callback, matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::ParamEditEventClass>(item, callback,
                                                             matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::ParamValueEventClass>(item, callback,
                                                              matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::ParamStringEventClass>(item, callback,
                                                               matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::ParamModeEventClass>(item, callback,
                                                             matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::ParamIncrementEventClass>(
      item, callback, matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::ParamColorEventClass>(item, callback,
                                                              matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::ParamRangeEventClass>(item, callback,
                                                              matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::ParamStringListEventClass>(
      item, callback, matched);
  if (matched)
    return result;
  result = bindActualItem<
      Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent8, 19778>>(
      item, callback, matched);
  if (matched)
    return result;
  result = bindActualItem<
      Presonus::UC::MeterEventClass<Presonus::UC::MeterEvent16, 19795>>(
      item, callback, matched);
  if (matched)
    return result;
  result =
      bindActualItem<Presonus::UC::TimeCodeEventClass>(item, callback, matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::MusicInputEventClass>(item, callback,
                                                              matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::PrimitiveEventClassNoMembers<
      Presonus::UC::KeepAliveEvent, 19265>>(item, callback, matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::FileRequestEventClass>(item, callback,
                                                               matched);
  if (matched)
    return result;
  result =
      bindActualItem<Presonus::UC::FileDataEventClass>(item, callback, matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::FileDataRateEventClass>(item, callback,
                                                                matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::FileAbortEventClass>(item, callback,
                                                             matched);
  if (matched)
    return result;
  result =
      bindActualItem<Presonus::UC::BinaryEventClass>(item, callback, matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::DataEventClass<
      Presonus::UC::EncodedMessageEvent<19021>, 19021>>(item, callback,
                                                        matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::DataEventClass<
      Presonus::UC::EncodedMessageEvent<23117>, 23117>>(item, callback,
                                                        matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::DataEventClass<
      Presonus::UC::EncodedMessageEvent<21826>, 21826>>(item, callback,
                                                        matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::DataEventClass<
      Presonus::UC::EncodedMessageEvent<23106>, 23106>>(item, callback,
                                                        matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::MessageChunkEventClass>(item, callback,
                                                                matched);
  if (matched)
    return result;
  result = bindActualItem<
      Presonus::UC::DataEventClass<Presonus::UC::LoopbackQueryEvent, 19537>>(
      item, callback, matched);
  if (matched)
    return result;
  result = bindActualItem<
      Presonus::UC::DataEventClass<Presonus::UC::LoopbackReplyEvent, 19538>>(
      item, callback, matched);
  if (matched)
    return result;
  result =
      bindActualItem<Presonus::UC::DebugEventClass>(item, callback, matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::MidiMessageEventClass>(item, callback,
                                                               matched);
  if (matched)
    return result;
  result = bindActualItem<Presonus::UC::MidiShortSysexEventClass>(
      item, callback, matched);
  if (matched)
    return result;
  result = bindActualItem<
      Presonus::UC::DataEventClass<Presonus::UC::MidiLongSysexEvent, 21324>>(
      item, callback, matched);
  if (matched)
    return result;
  throw std::logic_error("actual supported default-factory item required");
}
} // namespace
namespace Presonus::UC {
void Connection::dispatchReceived(EventItem *raw) {
  std::unique_ptr<EventItem> item(raw);
  auto &event = item->getData();
  auto &provider = presonus::uc::ConnectionSourceAccess::transport(*this);
  struct RemoveMapping {
    presonus::uc::ConnectionTransportProvider &provider;
    const Event *event;
    ~RemoveMapping() {
      provider.mappingPorts.erase(event);
      provider.loopbackQueries.erase(event);
    }
  } removeMapping{provider, &event};
  if (auto *query = dynamic_cast<presonus::uc::OwnedCodecItem<
          presonus::uc::OwnedDataPayload<LoopbackQueryEvent>> *>(item.get()))
    provider.loopbackQueries.emplace(&event, &query->value);
  if (event.routeA)
    event.routeA =
        static_cast<std::uint32_t>(makeLocalID(static_cast<int>(event.routeA)));
  adjustRouting(event, false);
  if (handleInternal(event))
    return;
  auto &dispatcher = presonus::uc::ConnectionSourceAccess::dispatcher(*this);
  auto binding = presonus::uc::DispatcherSourceAccess::values(dispatcher)
                     .bindIncoming(*item, event.type);
  const bool updated = dispatcher.updateEvent(event);
  binding.reset();
  if (!updated)
    dispatcher.queueEvent(item.release());
}
bool Connection::handleOwnedInternal(const Event &event) {
  if (event.type != 19537)
    return false;
  auto &provider = presonus::uc::ConnectionSourceAccess::transport(*this);
  const auto found = provider.loopbackQueries.find(&event);
  if (found == provider.loopbackQueries.end())
    throw std::logic_error("actual owning typed LoopbackQueryEvent required");
  presonus::uc::OwnedDataPayload<LoopbackReplyEvent> reply;
  reply.header = {19538, 24, event.routeB, event.routeA};
  reply.data = found->second->data;
  reply.sizeBits = found->second->sizeBits;
  auto &codec = presonus::uc::DefaultFactoryProvider<
      DataEventClass<LoopbackReplyEvent, 19538>>::get();
  codec.bind(reply);
  struct Unbind {
    decltype(codec) provider;
    decltype(reply) &value;
    ~Unbind() { provider.unbind(value); }
  } unbind{codec, reply};
  sendEvent(reply.header); // Native ignores the enqueue result.
  return true;
}
bool Connection::writeEvent(ChannelWriter &writer, const Event &event) {
  auto &provider = presonus::uc::ConnectionSourceAccess::transport(*this);
  std::array<unsigned char, 16384 + 6> frame;
  const int payload = provider.factory.write(
      reinterpret_cast<char *>(frame.data() + 6), 16384, event);
  if (payload <= 0)
    return false;
  frame[0] = 'U';
  frame[1] = 'C';
  frame[2] = 0;
  frame[3] = 1;
  frame[4] = static_cast<unsigned char>(payload);
  frame[5] = static_cast<unsigned char>(payload >> 8);
  const int size = payload + 6;
  if (size + writer.position > writer.capacity) {
    if (writer.position > 0) {
      const int pending = writer.position;
      const int written = writer.channel.write(writer.data, pending);
      writer.position = 0;
      if (written != pending)
        return false;
    }
    if (size > writer.capacity) {
      if (writer.channel.write(frame.data(), size) != size)
        return false;
    } else {
      std::memcpy(writer.data, frame.data(), static_cast<std::size_t>(size));
      writer.position = size;
    }
  } else {
    std::memcpy(writer.data + writer.position, frame.data(),
                static_cast<std::size_t>(size));
    writer.position += size;
  }
  provider.sentBytes += static_cast<std::uint64_t>(size);
  ++provider.sentEvents;
  const char *name = provider.connectionName.str();
  presonus::uc::NetworkActivityPortAccess::recordSent(
      presonus::uc::BasicConnectionSourceAccess::activity(*this),
      presonus::uc::BasicConnectionSourceAccess::connectionType(*this), event,
      size, name);
  return true;
}
bool Connection::writeEvents(bool drain) {
  auto &provider = presonus::uc::ConnectionSourceAccess::transport(*this);
  auto &queue = presonus::uc::BasicConnectionSourceAccess::queue(*this);
  ChannelWriter writer{
      *provider.channel,
      static_cast<unsigned char *>(provider.writeBuffer.getAddress()),
      static_cast<int>(state_.channelLimitBits)};
  while (!queue.isEmpty()) {
    if (!provider.channel->isWritable(10)) {
      if (drain)
        queue.flush();
      break;
    }
    std::unique_ptr<EventItem> item(queue.retrieveEvent());
    auto &event = item->getData();
    if (!withActualItem(*item, [&](Event &bound) {
          if (item->sourcePortTransportFlags == 1 && sendPeriodicEvent(bound))
            return true;
          adjustRouting(bound, true);
          return writeEvent(writer, bound);
        }))
      return false;
  }
  return writer.position <= 0 ||
         writer.channel.write(writer.data, writer.position) == writer.position;
}
bool Connection::process(bool drain) {
  auto &provider = presonus::uc::ConnectionSourceAccess::transport(*this);
  auto &queue = presonus::uc::BasicConnectionSourceAccess::queue(*this);
  if (!provider.channel)
    queue.flush();
  else if (readEvents()) {
    if (!writeEvents(drain))
      provider.failed = true;
  } else {
    if (!drain)
      provider.failed = true;
    else if (!writeEvents(drain))
      provider.failed = true;
  }
  // Native process is observed for side effects only; its return declaration
  // is unresolved and this portable bool means transport health.
  auto &received = presonus::uc::ConnectionSourceAccess::incomingQueue(*this);
  while (auto *item = received.retrieveEvent())
    dispatchReceived(item);
  return !provider.failed;
}
} // namespace Presonus::UC
