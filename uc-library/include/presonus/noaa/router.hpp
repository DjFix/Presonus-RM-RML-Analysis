#pragma once
#include "core/system/corethread.h"
#include "presonus/noaa/router_slot_tables.hpp"
#include "presonus/noaa/sysex_receiver.hpp"
#include <array>
#include <cstddef>
#include <optional>

namespace presonus::noaa {
class RouterSlotTables;
struct RouterLifecycleAccess;
// Independent real CCL timing plus genuine NOAA SPI idle adapter.
class CclRouterResponseRuntime final : public presonus::dice::IdlePump {
public:
  CclRouterResponseRuntime() : response_(*this) {}
  void onIdle(bool force) override;
  presonus::dice::ResponseServices &response() { return response_; }

private:
  presonus::dice::CclResponseServices response_;
};
// Independent byte storage for original offsets[0x18,0x920). Includes the
// original256-byte command region and adjacent application-state side effects;
// no original field declarations, Core lock storage or ARM object layout claim.
struct RouterState {
  RouterState() = default;
  // Independent owned-default setup: initialized application state precedes
  // actual CCL lock construction. Not an original RouterState declaration.
  explicit RouterState(const std::array<unsigned char, 2312> &bytes)
      : applicationBytes(bytes) {}
  RouterState(const RouterState &) = delete;
  RouterState &operator=(const RouterState &) = delete;
  std::array<unsigned char, 2312> applicationBytes;
  // Actual owned CCL source mutex. Its placement/size is not the old ARM
  // CoreLock layout; the legacy byte image deliberately ends before Core.
  Core::Threads::Lock lock;
  // Independent setup, required only by lookups. Bind an immutable view
  // before publication and retain it for every call; queue paths need none.
  const RouterSlotTables *slotTables = nullptr;
  // Copied view owns no bytes, but survives the setup-property temporary.
  std::optional<RouterSlotTables> ownedSlotTables;
};
// Independent, explicit compatibility input for reads beyond original64-byte
// g64RouteTable. These192bytes describe one fixed ET_EXEC link-address image,
// not a larger original array or an arbitrary runtime/hardware snapshot.
struct RouterLookupImage {
  std::array<unsigned char, 192> adjacentApplicationData;
};
const RouterLookupImage &rm13731LinkAddressRouterLookup();
} // namespace presonus::noaa

namespace Presonus::NOAA {
struct NOAASetupProperty;
// Portable four-byte representation established from byte loads/stride only.
// Original member declarations/names and wider ABI remain unresolved.
struct DiceRoute {
  unsigned char bytes[4];
};
static_assert(sizeof(DiceRoute) == 4 && offsetof(DiceRoute, bytes) == 0);
// Actual original RTTI: TCardRouter->NOAA::SysexReceiver; inherited table order
// receive/accepts/post, no added virtual destructor. Default C1/C2 and D1/D2
// are candidate source ports; original full layout/exception behavior remains
// unresolved. All calls/setup are serialized by the caller.
class TCardRouter : public SysexReceiver {
public:
  TCardRouter();
  // Modern source-port exception declaration; original spelling unresolved.
  // Neither original D1 nor D2 deallocates the Router object.
  ~TCardRouter() noexcept(false);
  // Independent required setup overload. Every borrowed input must outlive use;
  // production supplies genuine CCL-backed response/diagnostic/SPI services.
  TCardRouter(presonus::noaa::RouterState &state,
              presonus::dice::ResponseServices &response,
              presonus::noaa::SpiServiceIO &diagnostics,
              const presonus::noaa::RouterLookupImage &lookup)
      : state_(state), diagnostics_(diagnostics), lookup_(lookup) {
    setPortableResponseServices(response);
  }
  bool open(const NOAASetupProperty &property);
  // Original encoded parameter types; ordinary void returns remain pending.
  void setInputToAvbTxRoute(int unused, int destination, int input, int type);
  void setInputToDanteTxRoute(int unused, int destination, int input, int type,
                              int enabled);
  void setTalkbackToAvbTxRoute(int unused, int destination, int enabled);
  void set2TrackInputRoute(unsigned char left, unsigned char right);
  void setGEQToFWRoute(unsigned char slot, unsigned char destination);
  void setMixerMuteInputRoute(unsigned char channel, int muted);
  unsigned char lookupADCSlot(unsigned char value);
  unsigned char lookupDACSlot(unsigned char value);
  unsigned char lookupGeqSlot(unsigned char value);
  // Portable return spellings; original ordinary declarations remain pending.
  bool accepts(const SysexPacket &packet) override;
  void doRouteCommands(DiceRoute *routes, int count, unsigned char remap);
  bool addIdleRoute(unsigned char device0, unsigned char channel0,
                    unsigned char device1, unsigned char channel1);
  void idle();
  void doRouteCommand(unsigned char device0, unsigned char channel0,
                      unsigned char device1, unsigned char channel1,
                      unsigned char remap);

  // Original return spellings remain unresolved; portable void declarations.
  void setAvbToLinkBusRoute(int bus, int source, int destination, int count);
  void setLinkBusToAvbRoute(int unused, int destination, int source, int count);
  void setDspToDanteTxRoute(int bus, int destination, int source, int count);
  void setDspToAvbTxRoute(int bus, int destination, int source, int count,
                          bool muted);
  void setAvbTapeLRToAvbTxRoute(int unused, int destination, int enabled);
  void setAvbStageBoxMainRoute(int bus, int source, int enabled);

  // Original ordinary return declarations remain unresolved.
  void setGEQInsert(unsigned int slot, unsigned int enabled);
  void setGEQTDMSlotInsert(unsigned int slot, unsigned int channel,
                           unsigned int enabled);
  void setAvbToDacBypassRoute(int channel, int bus, int source, int count,
                              bool enabled);
  void setMixerCustomInputRoute(unsigned char source, unsigned char destination,
                                int mode, int bus);
  void setSPDIFRoute(unsigned char left, unsigned char right, int mode);
  void setAVS48Route(unsigned char destination, unsigned char source, int mode,
                     unsigned char bus);

  // Original encoded parameters; unencoded return declarations remain pending.
  void setAvbToSlaveFwRecordRoute(int bus, int source, int count, bool enabled);
  void setAvbTapeRxToDigitalReturnRoute(int bus, int source, bool enabled);
  void setMixerInputRoute(unsigned char channel, int mode, bool queued);

  // Original parameter identities; unencoded return declarations remain
  // pending.
  void routeAnalogIns(bool muted);
  void initRoutes();

  // Original encoded pointer/const scope; unencoded return spelling pending.
  void routeScript(const char *filename);

private:
  friend struct presonus::noaa::RouterLifecycleAccess;
  // Independent ownership/runtime fields, not recovered ARM class fields.
  std::optional<presonus::noaa::CclRouterResponseRuntime> ownedRuntime_;
  std::optional<presonus::noaa::RouterState> ownedState_;
  presonus::noaa::RouterState &state_;
  presonus::noaa::SpiServiceIO &diagnostics_;
  const presonus::noaa::RouterLookupImage &lookup_;
  // The independent borrowed-state overload never registers itself.
  bool registered_ = false;
};
} // namespace Presonus::NOAA

namespace presonus::noaa {
// Independent test/source-port inspection, no original method claims.
struct RouterLifecycleAccess {
  static RouterState &state(Presonus::NOAA::TCardRouter &router) {
    return router.state_;
  }
  static bool ownsState(const Presonus::NOAA::TCardRouter &router) {
    return router.ownedState_.has_value();
  }
  static bool registered(const Presonus::NOAA::TCardRouter &router) {
    return router.registered_;
  }
  static auto &runtime(Presonus::NOAA::TCardRouter &router) {
    return *router.ownedRuntime_;
  }
};
} // namespace presonus::noaa
