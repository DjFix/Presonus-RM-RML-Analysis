#pragma once
#include "presonus/avb/ComponentResource.hpp"
#include "presonus/uc/ServerComponent.hpp"
#include <array>
#include <cstdint>
namespace presonus::avb {
// Independent source-port types. These are not original class layouts.
struct Listener {
  std::uint8_t index{};
};
struct ListenerState {
  Listener *cascade{}, *mixer{}, *csInput{}, *console{};
  int linkMode{};
  std::uint32_t consoleSource{};
  ComponentResource *resource{};
};
struct RoutingPacket {
  std::array<std::uint32_t, 6> words{};
  bool enabled{};
};
class ListenerServices {
public:
  virtual ~ListenerServices() = default;
  virtual Listener *addListener(unsigned long long, unsigned short,
                                unsigned char) = 0;
  virtual void removeListener(Listener *) = 0;
  virtual void setAudioClockToListener(Listener *) = 0;
  virtual void configureStaticTalkerStreams() = 0;
  virtual void routeLinkSlotsFromAvb() = 0;
  virtual void sendRoutingPacket(const RoutingPacket &) = 0;
};
} // namespace presonus::avb
namespace presonus::avb {
struct AvbIdleMaintenanceAccess;
}
namespace Presonus::AVB {
class AvbTalker;

// Original encoded method names/parameters; independent portable storage and
// constructor. Original return declarations, inheritance and ARM layout
// pending.
class AvbComponent : public Presonus::UC::ServerComponent {
public:
  enum ListenerType : int { Cascade = 0, CSInput = 2, ConsoleBus = 3 };
  AvbComponent(presonus::avb::ListenerState &s,
               presonus::avb::ListenerServices &v)
      : state_(s), services_(v) {}
  ~AvbComponent() override;
  // Source-port void declaration; original ordinary return remains pending.
  void onIdle() override;
  // Portable void declaration; original return type remains unresolved.
  void handleTalkerStateChange(AvbTalker *);
  void configureStaticTalkerStreams();
  void routeLinkSlotsFromAvb();
  void setSpectrumDataTxSource(int, int);
  int getConsoleTalkbackListenerAndChannel(int *, int *);
  int getCSTalkbackListenerAndChannel(int *, int *);
  int getListenerAndChannelForInput(int *, int *, int, bool);
  int getTalkerAndChannelForInput(int *, int *, int);
  bool hasListeners() const;
  int getAVBListenerIndex(int) const;
  void addListener(ListenerType, long long, bool, int, bool);
  void addCSInputListener(long long, bool);
  void addMixerInputListener(long long, bool);
  void addCascadeListener(long long, bool);
  void addConsoleBusListener(long long, bool, int, bool);

private:
  friend struct presonus::avb::AvbIdleMaintenanceAccess;
  // Independent portable binding for the original per-class process static.
  static std::int64_t lastMaintenance_;
  presonus::avb::ListenerState &state_;
  presonus::avb::ListenerServices &services_;
};
} // namespace Presonus::AVB

namespace presonus::avb {
// Independent fixture/source-port access, not an original public interface.
struct AvbIdleMaintenanceAccess {
  static std::int64_t get() {
    return Presonus::AVB::AvbComponent::lastMaintenance_;
  }
  static void set(std::int64_t value) {
    Presonus::AVB::AvbComponent::lastMaintenance_ = value;
  }
};
} // namespace presonus::avb
