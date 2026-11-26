#pragma once
#include "core/public/corevector.h"
#include "core/system/corethread.h"
#include "presonus/uc/client_event_values.hpp"
#include "presonus/uc/connection_interfaces.hpp"
#include "presonus/uc/events.hpp"
#include "presonus/uc/network_manager_services.hpp"
#include <array>
#include <atomic>
#include <cstdint>
#include <map>
#include <stdexcept>
#include <variant>

namespace presonus::meter {
// Independent source-port provenance. Shared ownership keeps each actual typed
// value alive until unbind/registry destruction. Serialized use only; view
// aliases are checked before mutation and tags never grant mutable access.
class MutableMeterOrigins {
public:
  void bind(std::shared_ptr<Presonus::UC::MeterEvent8> value) {
    if (!value)
      throw std::invalid_argument("null meter owner");
    const auto *header = &value->header;
    owners_[header] = std::move(value);
  }
  void bind(std::shared_ptr<Presonus::UC::MeterEvent16> value) {
    if (!value)
      throw std::invalid_argument("null meter owner");
    const auto *header = &value->header;
    owners_[header] = std::move(value);
  }
  void unbind(const Presonus::UC::Event &header) { owners_.erase(&header); }
  Presonus::UC::Event &resolve(Presonus::UC::MeterEvent &view) const;

private:
  std::map<const Presonus::UC::Event *,
           std::variant<std::shared_ptr<Presonus::UC::MeterEvent8>,
                        std::shared_ptr<Presonus::UC::MeterEvent16>>>
      owners_;
};
struct ExternalTransportTag {};
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
class MeterMaid;
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
  MeterManagerBase(presonus::meter::ExternalTransportTag,
                   presonus::meter::Environment *environment,
                   UC::INetworkManager &network, UC::IConnection &external,
                   presonus::meter::MutableMeterOrigins &origins,
                   presonus::uc::Meter8FactoryCodec &envelopeCodec)
      : MeterManagerBase(environment, network) {
    external_ = &external;
    mutableOrigins_ = &origins;
    envelopeCodec_ = &envelopeCodec;
  }
  void sendToExternalClients(Core::FixedSizeVector<int, 100> &,
                             UC::MeterEvent &, int);
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

private:
  UC::IConnection *external_ = nullptr;
  presonus::meter::MutableMeterOrigins *mutableOrigins_ = nullptr;
  presonus::uc::Meter8FactoryCodec *envelopeCodec_ = nullptr;

protected:
  // The roster owns its non-null entries. The original return declaration
  // remains unresolved.
  void deleteAll(Core::Vector<MeterMaid *> &roster);

  // Default meter-processing hook for the portable base.
  virtual void processMeters(bool);
  virtual void sendUCNETMeters(bool);

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
