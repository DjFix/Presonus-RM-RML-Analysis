#pragma once
namespace Presonus::UC {
class NetworkItem;
}
namespace presonus::mixer {
// Independent source-port boundary. Not an original class or ABI declaration.
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
  void connect(UC::NetworkItem *);
  void onNetworkShutdown();
  bool isConnected(UC::NetworkItem *) const;
  void onNetworkItemRemoved(UC::NetworkItem *);
  void cardConnectionChanged(bool);
  bool sourcePortCardConnected() const { return cardConnected_; }

private:
  presonus::mixer::CascadeBoundary &boundary_;
  UC::NetworkItem *selected_;
  bool cardConnected_ = false;
};
} // namespace Presonus::Mixer
