#include "presonus/application/SurfaceApplication.hpp"
#include "presonus/uc/ClientRootComponent.hpp"

#include <iostream>
#include <new>
#include <type_traits>

namespace {
using presonus::application::SurfaceSerialStateAccess;
using Presonus::Surface::SurfaceApplication;
using Presonus::UC::ClientRootComponent;

struct TrackedClient final : ClientRootComponent {
  TrackedClient() : ClientRootComponent("tracked") {}
  ~TrackedClient() override { ++destroyed; }

  static void *operator new(std::size_t size) { return ::operator new(size); }

  static void operator delete(void *pointer) noexcept {
    receiverMatched = pointer == allocation;
    destructionPrecededRelease = destroyed == 1;
    ++released;
    ::operator delete(pointer);
  }

  static inline unsigned destroyed = 0;
  static inline unsigned released = 0;
  static inline bool receiverMatched = false;
  static inline bool destructionPrecededRelease = false;
  static inline void *allocation = nullptr;
};

void report(const char *name, SurfaceApplication &app, std::uint32_t before) {
  std::cout << name << ' ' << TrackedClient::destroyed << ' '
            << TrackedClient::released << ' ' << TrackedClient::receiverMatched
            << ' ' << TrackedClient::destructionPrecededRelease << ' '
            << (SurfaceSerialStateAccess::value(app) == before) << '\n';
}
} // namespace

int main() {
  static_assert(std::has_virtual_destructor_v<ClientRootComponent>);
  SurfaceApplication app{};
  constexpr std::uint32_t sentinel = 0x0756C9A5;
  SurfaceSerialStateAccess::seed(app, sentinel);

  app.releaseClientComponent(nullptr);
  report("null", app, sentinel);

  app.releaseClientComponent(new ClientRootComponent("concrete"));
  report("concrete", app, sentinel);

  auto *tracked = new TrackedClient;
  TrackedClient::allocation = tracked;
  app.releaseClientComponent(tracked);
  report("derived", app, sentinel);
}
