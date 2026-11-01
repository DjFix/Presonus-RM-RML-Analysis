#pragma once
#include "core/public/corevector.h"
#include "core/system/corethread.h"
#include "presonus/uc/events.hpp"
#include "presonus/uc/network_manager_services.hpp"
#include <array>
#include <atomic>
#include <cstdint>

namespace presonus::meter {
// Independent application boundary; not a recovered server/client class layout.
struct ClientView {
  int id;
  bool external;
  const char *subscriptions;
};
struct Environment {
  virtual ~Environment() = default;
  virtual bool serverAvailable() const { return true; }
  virtual int clientCount() const = 0;
  virtual ClientView clientAt(int index) const = 0;
  virtual bool hasClients() const = 0;
  virtual std::uint32_t sessionId() const = 0;
  virtual void tick(bool) = 0;
  virtual void clientTick(bool) = 0;
};
} // namespace presonus::meter

namespace Presonus {
// Portable source adaptation. Thread inheritance, storage and constructor are
// intentional CCL integration choices, not recovered original layout or ABI.
// Unencoded original return declarations remain pending; startup/shutdown and
// update/send use void, threadEntry follows the actual CCL int interface.
class MeterManagerBase : public Core::Threads::Thread {
public:
  explicit MeterManagerBase(presonus::meter::Environment *environment,
                            UC::INetworkManager &network)
      : Core::Threads::Thread("MeterManager"), environment(environment),
        network(network) {}
  void startup();
  void shutdown();
  int threadEntry() override;
  void updateClients();
  void sendToClients(Core::FixedSizeVector<int, 100> &, UC::Event &);

  // Explicit source-port state access, unrelated to original field
  // declarations.
  std::atomic<unsigned char> sourcePortRunning{0};
  std::atomic<bool> sourcePortStop{false};
  std::array<Core::FixedSizeVector<int, 100>, 6> sourcePortClients;

protected:
  // Test overrides capture external provider boundaries. Production defaults
  // invoke the real pinned CCL implementation; no fake Core provider exists.
  virtual void sourcePortStart();
  virtual bool sourcePortJoin(unsigned int);
  virtual void sourcePortTerminate();
  virtual void sourcePortSleep(unsigned int);
  presonus::meter::Environment *environment;
  UC::INetworkManager &network; // Borrowed actual source-port provider.
  Core::Threads::Lock sourcePortLock;
};
} // namespace Presonus
