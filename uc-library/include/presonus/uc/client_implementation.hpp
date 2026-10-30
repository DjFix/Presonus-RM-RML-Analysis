#pragma once
#include "core/public/corevector.h"
#include "presonus/uc/network_manager_services.hpp"
#include <cstdint>
namespace presonus::uc {
struct ClientStatePortTag {};
struct ClientStatePortAccess;
struct ClientDispatchPortTag {};
class EventOrigins;
class ClientTypedOrigins;
// Actual pinned source clock adapter, not a reconstructed original ELF method.
std::uint64_t clientSystemMilliseconds();
} // namespace presonus::uc
namespace Presonus::UC {
struct LoopbackReplyEvent;
struct ParamEvent;
struct MeterEvent;
struct TimeCodeEvent;
struct BinaryEvent;
struct DebugEvent;
class IFileTransferManager;
// Original callback names/scopes and twelve-slot ordering evidenced by both
// ClientRootComponent secondary tables. Callback return spellings and native
// member storage are portable choices; no original layout/ABI claim.
class ClientImplementation : public IEventHandler {
public:
  ClientImplementation(const ClientImplementation &) = delete;
  ClientImplementation &operator=(const ClientImplementation &) = delete;
  int handleEvent(void *, const Event &) override;
  virtual ~ClientImplementation();
  // The name/const clock slot is identified independently in the concrete
  // ClientRootComponent secondary vtable. Its original return declaration is
  // unresolved; unsigned64 preserves the tested clock-bit source projection.
  virtual std::uint64_t getSystemTime() const = 0;
  bool hasParamChanged(void *, int) const;
  void resetParamChanges();
  void resetParamChanges(void *);
  void setLastParamChange(void *);
  void markAlive();
  void keepAlive();
  int sendEvent(Event &);
  virtual void updateLevels(const MeterEvent &) = 0;
  virtual void receiveEvent(const TimeCodeEvent &) = 0;
  virtual void receiveEvent(const ParamEvent &) = 0;
  virtual void receiveEvent(const MessageEvent &) = 0;
  virtual void receiveEvent(const BinaryEvent &) = 0;
  virtual void receiveEvent(const DebugEvent &) = 0;
  virtual void receiveEvent(const LoopbackReplyEvent &);
  virtual void sendAllToServer() = 0;
  int connect(int, MessageEvent &);
  int disconnect(MessageEvent *);
  // Original nested type identity is encoded in the actual container calls.
  // Fields below are independent source-port values, not recovered ARM fields.
  struct ParamChange {
    void *context = nullptr;
    std::uint32_t opaqueWord = 0;
    std::uint64_t timeBits = 0;
  };

protected:
  ClientImplementation(presonus::uc::ClientStatePortTag, INetworkManager &,
                       std::uint32_t routeA, std::uint32_t routeB);
  // Independent injection constructor; original C1/C2 and lazy singleton
  // gateways stay unresolved. Referents outlive this Client and its callbacks.
  ClientImplementation(presonus::uc::ClientDispatchPortTag, INetworkManager &,
                       IFileTransferManager &, presonus::uc::EventOrigins &,
                       presonus::uc::ClientTypedOrigins &, std::uint32_t routeA,
                       std::uint32_t routeB);

private:
  friend struct presonus::uc::ClientStatePortAccess;
  INetworkManager &manager_;
  std::uint32_t routeA_, routeB_;
  std::uint64_t lastAlive_ = 0, untouchedBits_ = 0;
  Core::FixedSizeVector<ParamChange, 64> changes_;
  // New source-port injected services/provenance, not original ARM fields.
  IFileTransferManager *files_ = nullptr;
  presonus::uc::EventOrigins *eventOrigins_ = nullptr;
  presonus::uc::ClientTypedOrigins *typedOrigins_ = nullptr;
};
} // namespace Presonus::UC
namespace presonus::uc {
struct ClientStatePortAccess {
  static std::uint32_t
  routeB(const Presonus::UC::ClientImplementation &client) {
    return client.routeB_;
  }
  static auto &changes(Presonus::UC::ClientImplementation &client) {
    return client.changes_;
  }
  static auto &lastAlive(Presonus::UC::ClientImplementation &client) {
    return client.lastAlive_;
  }
  static auto &untouchedBits(Presonus::UC::ClientImplementation &client) {
    return client.untouchedBits_;
  }
};
} // namespace presonus::uc
