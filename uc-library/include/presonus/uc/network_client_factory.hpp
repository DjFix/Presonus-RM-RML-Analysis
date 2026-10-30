#pragma once
namespace Presonus::UC {
class NetworkItem;
class ClientRootComponent;
// Actual app interface:3pure slots, no added virtual destructor. Return types
// below are explicit source-port candidates, not recovered original
// declarations.
class INetworkClientFactory {
public:
  virtual bool isNetworkClientReady() const = 0;
  virtual ClientRootComponent *createClientComponent(const NetworkItem &) = 0;
  virtual void releaseClientComponent(ClientRootComponent *) = 0;

protected:
  ~INetworkClientFactory() = default;
};
} // namespace Presonus::UC
