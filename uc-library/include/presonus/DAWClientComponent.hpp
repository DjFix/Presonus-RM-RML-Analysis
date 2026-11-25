#pragma once

#include "presonus/surface/CapturePageComponent.hpp"
#include "presonus/uc/ClientRootComponent.hpp"

#include <cstdint>

namespace Presonus {

class IDAWDialogHandler;
class IDAWTimeInfo;
class IDAWTimeInfoFactory;

// Portable primary component. Native construction, secondary interfaces and
// object layout are outside this recovered subset.
class DAWClientComponent : public UC::ClientRootComponent {
public:
  static constexpr int kTypeID = 0x64774343;
  static constexpr int __typeid() { return kTypeID; }
  using ClientRootComponent::ClientRootComponent;

  void *castTo(int typeId) override;
  DAWChannel *getFocusChannel();
  void setFocusChannel(DAWChannel *channel);
  void channelsChanged(DAWChannelGroup *group);
  void slotCountChanged(DAWDeviceFolder *folder);
  void slotEditChanged(DAWDeviceSlot *slot, bool edit);
  void
  sendObjectChangeMessage(IDAWComponentObserver::ObjectChangeMessage message);
  bool isDAWProgressMode() const;
  void setDAWProgress(bool active);
  Core::Portable::Parameter *getLoopStartParam() const;
  Core::Portable::Parameter *getLoopEndParam() const;
  void setDialogHandler(IDAWDialogHandler *handler);
  IDAWTimeInfo *getTimeInfo() const;
  static void setTimeInfoFactory(IDAWTimeInfoFactory *factory);
  void optimize();
  Core::Portable::Component *getMixer() const;
  Core::Portable::Component *getControlLink() const;
  Core::Portable::Component *getDocument() const;
  Core::Portable::Component *getRecordDiskSpace() const;
  Core::Portable::Component *getSessionComponent() const;
  Core::Portable::Component *getRecordPanelComponent() const;
  Core::Portable::Component *getMetronomeComponent() const;

  // Source-port registration. Receivers are borrowed and must remain valid;
  // callbacks in this subset require a stable registration list.
  bool addSourcePortObserver(IDAWComponentObserver &observer);
  bool removeSourcePortObserver(IDAWComponentObserver &observer);

protected:
  // Portable state for derived application assembly. These declarations
  // neither encode ARM offsets nor imply ownership of borrowed interfaces.
  Core::Vector<IDAWComponentObserver *> observers_;
  DAWChannel *focusChannel_ = nullptr;
  IDAWDialogHandler *dialogHandler_ = nullptr;
  IDAWTimeInfo *timeInfo_ = nullptr;
  static IDAWTimeInfoFactory *timeInfoFactory_;
  std::uint32_t dawFlags_ = 0;
};

} // namespace Presonus
