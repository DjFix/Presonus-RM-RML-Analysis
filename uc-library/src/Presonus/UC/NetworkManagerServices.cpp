#include "presonus/uc/network_manager_services.hpp"
#include <cstring>
#include <stdexcept>

DEFINE_SINGLETON(Presonus::UC::NetworkManager)

namespace {
int signedBits(std::uint32_t value) {
  int result;
  std::memcpy(&result, &value, 4);
  return result;
}
bool dynamicSize(std::uint32_t tag) {
  return tag == 0x424f || tag == 0x5a4d || tag == 0x4a4d || tag == 0x5a42 ||
         tag == 0x5542 || tag == 0x4c51 || tag == 0x4c52 || tag == 0x534c;
}
bool chunkable(std::uint32_t tag) {
  return tag == 0x5a4d || tag == 0x4a4d || tag == 0x5a42 || tag == 0x5542;
}
} // namespace
namespace Presonus::UC {
int NetworkManager::registerHandler(int &identifier, IEventHandler *handler) {
  identifier = state_.dispatcher.addHandler(handler, 0);
  return 0;
}
int NetworkManager::unregisterHandler(IEventHandler *handler) {
  return state_.dispatcher.removeHandler(handler) ? 0 : 100;
}
int NetworkManager::sendEvent(const Event &event, int flags) {
  std::uint32_t size = event.reserved04;
  if (dynamicSize(event.type))
    size += state_.messageView(state_.context, event).sizeBits;
  if (signedBits(size) > 16384) {
    if (chunkable(event.type) && flags == 0)
      return sendChunks(state_.messageView(state_.context, event));
    state_.reportOversized(state_.context);
    return 103;
  }
  if (state_.dispatcher.updateEvent(event))
    return 0;
  auto *item = state_.factory.create(event);
  if (!item)
    return 101;
  state_.storeFlags(state_.context, *item, flags);
  state_.dispatcher.queueEvent(item);
  return 0;
}
int NetworkManager::sendChunks(const MessageEvent &event) {
  int remaining = signedBits(event.sizeBits);
  std::uint32_t offset = 0;
  while (remaining > 0) {
    const auto count =
        static_cast<std::uint32_t>(remaining < 0x3f80 ? remaining : 0x3f80);
    MessageChunkEvent chunk;
    chunk.header = {0x434b, 36, event.header.routeA, event.header.routeB};
    chunk.data = static_cast<const unsigned char *>(event.data) + offset;
    chunk.sizeBits = count;
    chunk.word24 = event.header.type;
    chunk.word28 = offset;
    chunk.word32 = event.sizeBits;
    auto *item = state_.factory.create(chunk.header);
    if (!item)
      return 103;
    state_.dispatcher.queueEvent(item);
    remaining -= static_cast<int>(count);
    offset += count;
  }
  return 0;
}
int NetworkManager::handleEvent(void *context, const Event &event) {
  if (event.type != 0x434b) {
    for (int n = 0; n < state_.handlers.count(); ++n) {
      const int result = state_.handlers.at(n)->handleEvent(context, event);
      if (result == 1)
        return 1;
      if (result == 2)
        break;
    }
    return 0;
  }
  const auto &chunk = state_.chunkView(state_.context, event);
  if (chunk.sizeBits + chunk.word28 < chunk.word32) {
    if (!context)
      throw std::invalid_argument("live pending chunk item required");
    state_.pendingChunks.append(static_cast<EventItem *>(context));
    return 1;
  }
  auto *item = state_.factory.createType(0x4a4d);
  if (!item)
    throw std::bad_alloc(); // Defined source guard outside success domain.
  auto &message = state_.messageItemView(state_.context, *item);
  message.header.type = chunk.word24;
  message.header.routeA = chunk.header.routeA;
  message.header.routeB = chunk.header.routeB;
  auto &storage = state_.storage(state_.context, *item);
  if (!storage.resize(chunk.word32)) {
    delete item;
    throw std::bad_alloc();
  }
  message.data = storage.getAddress();
  message.sizeBits = storage.getSize();
  storage.copyFrom(chunk.word28, chunk.data, chunk.sizeBits);
  if (chunk.word28 != 0) {
    Core::ListIterator<EventItem *> cursor(state_.pendingChunks);
    while (!cursor.done()) {
      auto *pending = cursor.next();
      const auto &earlier =
          state_.chunkView(state_.context, pending->getData());
      if (earlier.header.routeA != chunk.header.routeA ||
          earlier.header.routeB != chunk.header.routeB ||
          earlier.word24 != chunk.word24 || earlier.word32 != chunk.word32)
        continue;
      storage.copyFrom(earlier.word28, earlier.data, earlier.sizeBits);
      state_.pendingChunks.remove(pending);
      delete pending;
    }
  }
  state_.dispatcher.dispatchOne(item);
  return 0;
}
} // namespace Presonus::UC
