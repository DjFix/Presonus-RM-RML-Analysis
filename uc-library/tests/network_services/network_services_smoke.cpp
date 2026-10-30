#include "fixture_manager.hpp"
#include "presonus/uc/ccl_bindings.hpp"
#include <algorithm>
#include <iostream>
#include <map>
#include <vector>
using namespace Presonus::UC;
namespace {
void check(bool v) {
  if (!v)
    throw std::runtime_error("network smoke check");
}
struct Item final : EventItem {
  Core::IO::Buffer storage;
  MessageEvent message;
  MessageChunkEvent chunk;
  bool isChunk = false;
  int flags = 0;
  Event &getData() override { return isChunk ? chunk.header : message.header; }
};
struct Provider {
  presonus::uc::CclFactoryRegistry registry;
  EventFactory factory{registry.registry()};
  presonus::uc::FactoryCodec messageCodec{}, chunkCodec{};
  int rejects = 0;
  Provider() {
    for (auto *codec : {&messageCodec, &chunkCodec}) {
      codec->context = this;
      codec->create = [](void *) -> EventItem * {
        auto *i = new Item;
        i->message.header = {0x4a4d, 24, 0, 0};
        return i;
      };
      codec->clone = [](void *, const Event &event) -> EventItem * {
        auto *i = new Item;
        i->isChunk = event.type == 0x434b;
        const void *data = nullptr;
        unsigned size = 0;
        if (i->isChunk) {
          i->chunk = *reinterpret_cast<const MessageChunkEvent *>(&event);
          data = i->chunk.data;
          size = i->chunk.sizeBits;
        } else {
          i->message = *reinterpret_cast<const MessageEvent *>(&event);
          data = i->message.data;
          size = i->message.sizeBits;
        }
        if (!i->storage.resize(size)) {
          delete i;
          throw std::bad_alloc();
        }
        if (size)
          i->storage.copyFrom(data, size);
        if (i->isChunk)
          i->chunk.data = i->storage.getAddress();
        else
          i->message.data = i->storage.getAddress();
        return i;
      };
      codec->write = [](void *, BufferWriter &w, const Event &e) {
        return EventClass{}.write(w, e);
      };
      codec->read = [](void *, EventItem *i, BufferReader &r) {
        return i && EventClass{}.read(i->getData(), r);
      };
      codec->destroy = [](void *, EventItem *i) { delete i; };
    }
    registry.registry().append(0x4a4d, &messageCodec);
    registry.registry().append(0x434b, &chunkCodec);
  }
  void bind(presonus::uc::NetworkManagerState &state) {
    state.context = this;
    state.messageView = [](void *, const Event &e) -> const MessageEvent & {
      return *reinterpret_cast<const MessageEvent *>(&e);
    };
    state.messageItemView = [](void *, EventItem &i) -> MessageEvent & {
      return static_cast<Item &>(i).message;
    };
    state.chunkView = [](void *, const Event &e) -> const MessageChunkEvent & {
      return *reinterpret_cast<const MessageChunkEvent *>(&e);
    };
    state.storage = [](void *, EventItem &i) -> Core::IO::Buffer & {
      return static_cast<Item &>(i).storage;
    };
    state.storeFlags = [](void *, EventItem &i, int flags) {
      static_cast<Item &>(i).flags = flags;
    };
    state.reportOversized = [](void *p) {
      ++static_cast<Provider *>(p)->rejects;
    };
  }
};
struct Handler final : IEventHandler {
  unsigned calls = 0;
  std::vector<unsigned char> bytes;
  int handleEvent(void *, const Event &e) override {
    ++calls;
    const auto &m = *reinterpret_cast<const MessageEvent *>(&e);
    const auto *p = static_cast<const unsigned char *>(m.data);
    if (m.sizeBits)
      bytes.assign(p, p + m.sizeBits);
    return 0;
  }
};
} // namespace
int main() {
  try {
    Provider provider;
    presonus::uc::EventDispatcherState dispatcherState;
    EventDispatcher dispatcher(dispatcherState);
    presonus::uc::NetworkManagerState state{dispatcher, provider.factory};
    provider.bind(state);
    FixtureManager network(state);
    Handler handler;
    int id = -1;
    check(network.registerHandler(id, &handler) == 0 && id == 100);
    std::vector<unsigned char> payload(40000);
    for (unsigned n = 0; n < payload.size(); ++n)
      payload[n] = static_cast<unsigned char>(n * 73 + 17);
    MessageEvent event{
        {0x4a4d, 24, 31, static_cast<unsigned>(id)}, payload.data(), 32};
    check(network.sendEvent(event.header, 7) == 0 &&
          dispatcherState.queued.count() == 1);
    auto *queued = static_cast<Item *>(dispatcherState.queued.getFirst());
    check(queued->flags == 7 && queued->message.data != payload.data());
    dispatcher.dispatchAll();
    check(handler.calls == 1 &&
          handler.bytes == std::vector<unsigned char>(payload.begin(),
                                                      payload.begin() + 32));
    event.sizeBits = 40000;
    check(network.sendEvent(event.header, 1) == 103 && provider.rejects == 1 &&
          dispatcherState.queued.isEmpty());
    check(network.sendEvent(event.header, 0) == 0 &&
          dispatcherState.queued.count() == 3);
    unsigned received = 0;
    while (auto *p = dispatcherState.retrieve()) {
      auto *item = static_cast<Item *>(p);
      check(item->isChunk);
      const int retained = network.handleEvent(item, item->chunk.header);
      if (retained != 1)
        delete item;
      ++received;
    }
    check(received == 3 && state.pendingChunks.isEmpty() &&
          handler.calls == 2 && handler.bytes == payload);
    check(network.unregisterHandler(&handler) == 0 &&
          network.unregisterHandler(&handler) == 100);
    std::cout << "actual CCL factory/dispatcher registration, clone/flags, "
                 "oversized rejection and 40000-byte chunk reassembly PASS\n";
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
