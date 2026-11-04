#pragma once
#include <cstdint>
#include <stdexcept>
#include <vector>
namespace presonus::uc {
class ClientTypedOrigins;
}
namespace Core::Portable {
class Component;
class Parameter;
} // namespace Core::Portable
namespace Presonus::UC {
class ClientImplementation;
struct Event;
class NetworkItem;
} // namespace Presonus::UC
namespace presonus::mixer {
// Independent source-port boundary. Not an original class or ABI declaration.
// Independent borrowed state mapping, not an original component layout.
// Independent required boundary for observed nullable peer slot0x28.
// No original target type/vtable or implementation is established.
struct CascadeIdleTarget {
  virtual void onIdle() = 0;

protected:
  ~CascadeIdleTarget() = default;
};
// Borrowed typed views join an actual item component identity to existing
// real providers without guessing an original multiple-inheritance layout.
struct CascadeClientBinding {
  void *identity = nullptr;
  Core::Portable::Component *component = nullptr;
  Presonus::UC::ClientImplementation *client = nullptr;
};
struct CascadeComponentId {
  const void *component;
  const std::uint32_t *borrowedId;
};
struct CascadeBoundary {
  virtual ~CascadeBoundary() = default;
  virtual void select(Presonus::UC::NetworkItem *, bool) = 0;
  virtual bool connectedClientPresent() = 0;
  virtual void connectionChanged(bool) = 0;
  virtual void updateChannelSelectionSync() = 0;
};
} // namespace presonus::mixer
namespace Presonus::Mixer {
// Portable source port: layout, inheritance and original return declarations
// unresolved.
class AVBCascadeManager {
public:
  AVBCascadeManager(presonus::mixer::CascadeBoundary &boundary,
                    UC::NetworkItem *selected)
      : boundary_(boundary), selected_(selected) {}
  // Independent source-port setup; entries and ID storage must outlive reads.
  void sourcePortBindComponentIds(
      std::vector<presonus::mixer::CascadeComponentId> entries) {
    componentIds_ = entries;
  }
  void sourcePortBindClients(
      std::vector<presonus::mixer::CascadeClientBinding> entries) {
    clientBindings_ = entries;
  }
  void *getConnectedClient() const;
  void *getConnectedClientComponent() const;
  Core::Portable::Parameter *getSlaveParam(int) const;
  void sendEvent(UC::Event &);
  // Borrowed registry must also back the concrete NetworkManager messageView.
  // It outlives this manager and every synchronous message dispatch.
  void sourcePortBindMessageOrigins(presonus::uc::ClientTypedOrigins &origins) {
    messageOrigins_ = &origins;
  }
  presonus::uc::ClientTypedOrigins &sourcePortMessageOrigins() const;
  void presetStored(const char *, int);
  void presetRecalled(const char *, int);
  void muteGroupStored(int);
  void onIdle();
  void sourcePortBindIdle(presonus::mixer::CascadeIdleTarget *target) {
    idleTarget_ = target;
  }
  std::uint32_t getSlaveId() const; // Original return declaration unresolved.
  void connect(UC::NetworkItem *);
  void onNetworkShutdown();
  bool isConnected(UC::NetworkItem *) const;
  void onNetworkItemRemoved(UC::NetworkItem *);
  void cardConnectionChanged(bool);
  bool sourcePortCardConnected() const { return cardConnected_; }

private:
  const presonus::mixer::CascadeClientBinding &binding(void *) const;
  std::vector<presonus::mixer::CascadeClientBinding> clientBindings_;
  presonus::uc::ClientTypedOrigins *messageOrigins_ = nullptr;
  presonus::mixer::CascadeBoundary &boundary_;
  UC::NetworkItem *selected_;
  bool cardConnected_ = false;
  presonus::mixer::CascadeIdleTarget *idleTarget_ = nullptr;
  std::vector<presonus::mixer::CascadeComponentId> componentIds_;
};
} // namespace Presonus::Mixer
