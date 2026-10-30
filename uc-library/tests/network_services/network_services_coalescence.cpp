#include "fixture_manager.hpp"
#include "presonus/uc/ccl_bindings.hpp"
#include "presonus/uc/typed_factory_codec.hpp"
#include <cstring>
#include <iostream>
using namespace Presonus::UC;
int main() {
  try {
    unsigned rate, id, flags, a, b, reserved;
    while (std::cin >> rate >> id >> flags >> a >> b >> reserved) {
      if (reserved > 16384)
        throw std::runtime_error("coalescence size domain");
      presonus::uc::CclFactoryRegistry registry;
      EventFactory factory(registry.registry());
      presonus::uc::EventDispatcherState ds;
      EventDispatcher dispatcher(ds);
      ds.typedValue = [](void *, const Event &e,
                         presonus::uc::QueueValueKind kind) -> void * {
        if (kind != presonus::uc::QueueValueKind::FileRate)
          throw std::runtime_error("typed queue domain");
        return const_cast<FileDataRateEvent *>(
            reinterpret_cast<const FileDataRateEvent *>(&e));
      };
      presonus::uc::NetworkManagerState state{dispatcher, factory};
      state.storeFlags = [](void *, EventItem &, int) {
        throw std::runtime_error("coalesced event must retain prior flags");
      };
      state.reportOversized = [](void *) {
        throw std::runtime_error("unexpected coalescence oversize");
      };
      FixtureManager network(state);
      auto *queued = new presonus::uc::TypedEventItem<FileDataRateEvent>;
      queued->value.header = {0x4653, 0x12345678, a, b};
      queued->value.idBits = id;
      queued->value.wordBits = {0xdeadbeef, 123, 456};
      dispatcher.queueEvent(queued);
      FileDataRateEvent event;
      event.header = {0x4653, reserved, a, b};
      event.idBits = id;
      event.wordBits = {rate, 999, 7};
      int signedFlags;
      std::memcpy(&signedFlags, &flags, 4);
      const int result = network.sendEvent(event.header, signedFlags);
      if (result != 0 || ds.queued.count() != 1 ||
          ds.queued.getFirst() != queued ||
          queued->value.wordBits !=
              std::array<std::uint32_t, 3>{rate, 123, 456})
        throw std::runtime_error("coalescence result");
      std::cout << result << "|1|" << queued->value.header.type << ' '
                << queued->value.header.reserved04 << ' ' << a << ' ' << b
                << ' ' << id;
      for (auto word : queued->value.wordBits)
        std::cout << ' ' << word;
      std::cout << '\n';
      delete ds.queued.removeFirst();
    }
    if (!std::cin.eof())
      throw std::runtime_error("bad coalescence input");
  } catch (const std::exception &e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
