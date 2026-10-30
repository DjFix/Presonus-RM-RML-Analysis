#pragma once
namespace Presonus::UC {
class IDiscoveryReplyHandler;
struct DiscoveryDescriptor;
// Original 10-slot pure interface; return spellings are portable choices,
// not original declaration/ABI recovery. No fabricated lifecycle methods.
class IDiscoveryHandler {
public:
  virtual void setReplyHandler(IDiscoveryReplyHandler *) = 0;
  virtual bool startup(bool) = 0;
  virtual void shutdown() = 0;
  virtual bool startBrowsing() = 0;
  virtual void stopBrowsing() = 0;
  virtual void restartBrowsing() = 0;
  virtual bool registerServer(void *&, const DiscoveryDescriptor &, int) = 0;
  virtual void unregisterServer(void *) = 0;
  virtual void updateServer(void *, const char *) = 0;
  virtual void processDiscovery() = 0;

protected:
  ~IDiscoveryHandler() = default;
};
} // namespace Presonus::UC
