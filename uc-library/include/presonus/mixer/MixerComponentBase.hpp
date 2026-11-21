#pragma once
#include "core/portable/corecomponent.h"
#include "core/portable/corefilename.h"
#include "core/portable/corestorage.h"
#include "core/public/coreproperty.h"
#include "core/public/corevector.h"
#include <cstdint>
#include <functional>
#include <utility>
namespace presonus::panel {
class PresetApplicationServices;
}
namespace Presonus::UC {
class ClientSubscription;
}
namespace Presonus::NOAA {
class TCardHandler;
struct NOAAStatusProperty;
} // namespace Presonus::NOAA
namespace Presonus::Mixer {
class ChannelComponent;
class MasterSectionComponent;
class MixerComponent;
class PermissionsComponent;
class RackMixerComponent;
// Portable state model. Fields and return declarations are source-port choices,
// not recovered ARM layout or independently established original declarations.
class MixerComponentBase {
public:
  // One distinct borrowed real settings provider for native mixer+0x2dc.
  // Never implicitly aliases saveServices.parameters. Settings, cached params,
  // channel collection and its parameter identities must outlive SceneFilter.
  Core::Portable::Component *sceneSettings = nullptr;
  // Intentional port state for native +0x364; not an original field claim.
  bool sceneRecallBlocksTag14 = false;
  // Borrow the authoritative channel collection corresponding to native
  // mixer+0x11c Vector storage (+0x120 items / +0x124 count). The original
  // collection's friendly name is unresolved; never assume inputChannels.
  // Null explicitly denotes an empty collection in this source port.
  const Core::Vector<ChannelComponent *> *sceneChannels = nullptr;
  // Distinct borrowed actual CCL views for the partial composition facade.
  // +0x310's selected child and the original base child graph remain separate;
  // no original inheritance/layout is established by these source-port views.
  Core::Portable::Component *childLookupParameters = nullptr;
  Core::Portable::Component *selectedChildParameters = nullptr;
  Core::Portable::Component *findChild(const char *name) const;
  bool isSubgroupMerge() const;
  // Native +0x2d8, distinct from sceneSettings and routeInputParameters.
  // Required valid provider containing actual NumericParam tags 1 through 11.
  Core::Portable::Component *digitalOutputParameters = nullptr;
  void refreshDigitalOutputRoutes();
  int countSolos(int selector) const;
  void setChannelParams(int tag, float value);
  // Separate authoritative views for native +0x134 and +0x148. In the
  // portable source port a null view denotes an empty collection.
  const Core::Vector<ChannelComponent *> *sipSoloChannels = nullptr;
  const Core::Vector<ChannelComponent *> *tapeInputChannels = nullptr;
  // Borrowed required recipient for both solo-clear operations.
  MasterSectionComponent *soloMasterSection = nullptr;
  void clearSolos();
  void clearSIPSolos();
  // Portable bindings for native restore-mutes receiver and borrowed
  // Attributes at +0x384. The snapshot flag models native byte +0x366.
  MixerComponent *sipMuteRestorer = nullptr;
  Core::Portable::Attributes *sipMuteSnapshot = nullptr;
  bool sipMuteSnapshotPending = false;
  void activateSIP(bool active);
  void refreshSip();
  // Portable projections of the original route receiver and rack override.
  // Bind only the rack provider whose base is this source-port mixer.
  NOAA::TCardHandler *digitalRouteHandler = nullptr;
  // Borrow the existing NOAA stat projection bound to digitalRouteHandler.
  // Calls use its live metadata only. Serialize calls with other status users.
  NOAA::NOAAStatusProperty *serialStatus = nullptr;
  // Portable void declaration; original return declaration remains unresolved.
  void getMixerSerialInfo(int &, int &);
  // Portable bool for the observed 0/1 result; original declaration pending.
  bool hasDanteInputRoutes();
  RackMixerComponent *rackDigitalRoutes = nullptr;
  bool digitalOutputRouteDirty = false;
  void routeDigitalOutput(int output, int selection);
  // This property models the exact Setu payload for this producer, distinct
  // from the narrower portable DSP setup interface. Word names document
  // observations only; the original C++ static return type remains unresolved.
  struct MixerSetupProperty : Core::Property {
    MixerSetupProperty() : Core::Property(0x53657475, 40) {}
    float sampleRate = 0.f;
    std::uint32_t word0c = 0, word10 = 44, word14 = 24, word18 = 0;
    std::int32_t tag43 = 0, tag5 = 0, tag44 = 0;
  };
  MixerSetupProperty getSetupProperty() const;
  // The original returns the matching channel pointer before RTTI adjustment.
  ChannelComponent *getTapeIn() const;
  // Actual CCL parent supplies the native +0x210 child-list role.
  Core::Portable::Component *resetComponentParent = nullptr;
  void checkResetComponents(const Core::Portable::IStorageFilter &filter);
  // Independent native +0x19c word, pending a recovered typed identity.
  std::uint32_t tdmConfigWord = 0;
  // Borrow only the final observed byte of original +0x1fc -> ptrA ->
  // ptrB+0x234. Storage must remain valid on the route-byte branch; other
  // branches ignore it.
  const std::uint8_t *routeByteView = nullptr;
  void getTDMRoutes(int selector, unsigned char &first, unsigned char &second,
                    unsigned int &count);
  class Delegate;
  // Required borrowed application binding for preset construction. The same
  // real service instance must outlive constructed preset components.
  presonus::panel::PresetApplicationServices *presetApplicationServices =
      nullptr;
  // Independent portable state; no original layout or ownership claim.
  Core::Vector<Delegate *> delegates;
  // Borrowed duplicates are retained. Allocation failure leaves the list
  // unchanged. void is a source-port declaration, not established original
  // return type.
  void addDelegate(Delegate &delegate);
  void removeDelegate(Delegate &delegate);
  void faderLocateDirty(ChannelComponent *channel);
  bool shouldCollectFaderChanges(int selector) const;
  // Required independent identity query, not recovered Channel fields.
  std::function<std::pair<std::int32_t, std::int32_t>(ChannelComponent *)>
      channelIdentity;
  Core::Vector<ChannelComponent *> inputChannels, mixChannels;
  ChannelComponent *getLinkableChannelPair(ChannelComponent *) const;
  // Independent source-port contract moved from the competing definition;
  // original Filter layout remains unresolved.
  struct Filter {
    int selector{};
  };
  std::uint32_t selectedChannel = 0;
  std::uint32_t clientCount = 0;
  std::uint32_t hardwareMicLineInputs = 0;
  bool tryingToQuit = false;
  std::uint32_t getSelectedChannel() const;
  std::uint32_t numClients() const;
  const UC::ClientSubscription *getClient(int index) const;
  // Explicitly bind the legacy independent count API to one real collection.
  // Borrowed entries (including null slots) outlive calls. Once bound, callers
  // must preserve clientCount == clients_.count(); mismatches fail explicitly.
  void bindClients(const Core::Vector<const UC::ClientSubscription *> &clients);

private:
  Core::Vector<const UC::ClientSubscription *> clients_;
  bool clientsBound_ = false;
  void validateClients() const;

public:
  std::uint32_t numHWMicLineIn() const;
  const char *getCompanyName() const;
  std::uint32_t getSpectrumSendSlot() const;
  void setTryingToQuit();
  // Independent source-port bindings, not original object fields/layout.
  // Bound naming reuses inputChannels; no independent mirror vector.
  std::function<Core::Portable::Component *(ChannelComponent *)>
      channelParameters;
  bool inputChannelNamingBound = false;
  void bindInputChannelNaming(
      std::function<Core::Portable::Component *(ChannelComponent *)> resolver);
  void validateInputChannelBinding() const;
  Core::Portable::Component *cascadeParameters = nullptr;
  PermissionsComponent *permissions = nullptr;
  bool cascadeStatePending = false;
  Core::Portable::FileName applicationDataRoot;
  Core::CString256 deviceDataFolder;
  Core::Portable::FileName getDataDir(const char *subdir) const;
  bool isSlave();
  bool isMaster();
  void validateChannelNaming();
  // Borrowed real CCL tree for the portable routing source port. The caller
  // keeps the tree alive through routing and synchronous observer callbacks.
  // hardwareMicLineInputs supplies native +0x1d8's signed 32-bit loop bound;
  // this correspondence does not establish original fields or object layout.
  Core::Portable::Component *routeInputParameters = nullptr;
  // void is a source-port choice; original return declaration is unresolved.
  void routeInputsToNet();
  void resetPermissionsPW();
  void onCascadeStateChange();
  // Application-specific cache/path/filter/notification policies remain
  // mandatory source-port contracts. Actual storage and tasks come from CCL.
  struct CacheInfo {
    bool found = false;
    Core::Portable::FileName directory;
    Core::Portable::FileName obsoleteFile;
    int itemCount = 0;
  };
  struct SaveServices {
    Core::Portable::Component *parameters = nullptr;
    std::function<CacheInfo(const Core::Portable::FileName &)> inspectCache;
    std::function<void(const CacheInfo &)> refreshCache;
    std::function<Core::Portable::FileName(Core::ConstString)> localFile;
    std::function<int(int, Core::Portable::Component *)> saveFlags;
    std::function<void(Core::Portable::OutputStorage &, int)> configureStorage;
    std::function<void(Core::Portable::FileName, const char *, const char *,
                       int)>
        completed;
    std::function<void(const char *, int)> cascadePresetStored;
  } saveServices;
  Core::Portable::FileName findLocalFile(Core::ConstString name) const;
  void presetSaved(Core::Portable::FileName, const char *, const char *, int);
  bool savePreset(const Core::Portable::FileName &, const char *,
                  Core::ConstString);
  bool saveScene(const Core::Portable::FileName &, const char *, bool);
};
} // namespace Presonus::Mixer
