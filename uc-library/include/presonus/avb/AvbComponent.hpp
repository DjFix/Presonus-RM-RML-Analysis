#pragma once
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
namespace Presonus::AVB {
// Original encoded method names/parameters; independent portable storage and
// constructor. Original return declarations, inheritance and ARM layout
// pending.
class AvbComponent {
public:
  enum ListenerType : int { Cascade = 0, CSInput = 2, ConsoleBus = 3 };
  AvbComponent(presonus::avb::ListenerState &s,
               presonus::avb::ListenerServices &v)
      : state_(s), services_(v) {}
  void addListener(ListenerType, long long, bool, int, bool);
  void addCSInputListener(long long, bool);
  void addMixerInputListener(long long, bool);
  void addCascadeListener(long long, bool);
  void addConsoleBusListener(long long, bool, int, bool);

private:
  presonus::avb::ListenerState &state_;
  presonus::avb::ListenerServices &services_;
};
} // namespace Presonus::AVB
