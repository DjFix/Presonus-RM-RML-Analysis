#pragma once
#include "presonus/dice/packet_services.hpp"
#include "presonus/dice/response_services.hpp"
#include "presonus/dice/sysex_receiver_interface.hpp"
#include <array>

namespace Core::Threads {
class Lock;
}

namespace presonus::dice {
class SubsystemRuntime;
// Explicit independent setup overload for non-lifecycle fixtures/borrowed
// ports.
struct BorrowedSubsystemSetup {};
} // namespace presonus::dice

namespace Presonus::DICE {
// Portable state, not an original ARM layout, inheritance or ownership claim.
class SysexPacket {
public:
  // Independent setup construction retained for existing portable callers.
  SysexPacket() = default;
  SysexPacket(const unsigned char *data, unsigned char length);
  std::array<unsigned char, 256> bytes{};
  unsigned char length = 0;
  // Original constructor leaves data[255] untouched. Portable storage above
  // initializes it to zero; constructor equivalence excludes this inactive tail
  // and original padding. No indeterminate C++ read is used or required.
  presonus::dice::PacketMetadata &portableMetadata() { return metadata_; }
  const presonus::dice::PacketMetadata &portableMetadata() const {
    return metadata_;
  }
  // Binary proves a pointer return; returned-character const qualification is
  // unresolved. Unknown commands retain shared mutable static storage.
  const char *getSysexCommandStr(unsigned char command) const;
  // CANDIDATE void: original ordinary return declaration is pending.
  void log() const;

private:
  presonus::dice::PacketMetadata metadata_;
};

// Original enum identities; underlying type/enumerator spelling unresolved.
enum Dice3SampleRate : int {};
enum Dice3ClockSource : int {};
enum Dice3AudioSinkDevice : int {};
enum Dice3AudioSink : int {};
enum Dice3AudioSourceDevice : int {};
enum Dice3AudioSource : int {};

class SysexReceiver : public ISysexReceiver {
public:
  // Original constructor identity; storage is an independent portable layout.
  // Only command/status and the separate raw receiver +0x8 word are
  // original-body verified; derived infoWords begin at original +0xc.
  SysexReceiver();
  // Portable numeric choices; original return spelling is unencoded.
  unsigned char waitAck(long long timeout);
  bool waitResponseSet(unsigned int &response, long long timeout);
  // Setup only: bind services before publication; they outlive concurrent
  // waits.
  void setPortableResponseServices(presonus::dice::ResponseServices &services) {
    responseServices_ = &services;
  }
  // Independent source synchronization; bind once before publication. The
  // actual CCL lock must outlive this receiver and every concurrent user.
  void setPortableStateLock(Core::Threads::Lock *lock);
  presonus::dice::SubsystemState snapshotPortableState() const;
  void markPortableInfoPending();
  // CANDIDATE void: side-effect port only, original return declaration pending.
  void receive(const SysexPacket &packet) override;
  // Original table proves virtual post after receive/pure accepts.
  // CANDIDATE void: original ordinary return declaration remains unresolved.
  virtual void post(SysexPacket &packet);
  // Unsynchronized references are for single-thread fixtures/setup only.
  // Concurrent production uses guarded operations and value snapshots.
  presonus::dice::SubsystemState &portableState() { return state_; }
  // Independent raw word corresponding to original receiver +0x8. It is
  // distinct from subsystem infoWords[0], which corresponds to derived +0xc.
  // Single-thread fixture/setup reference only; concurrent publishers must
  // use the bound state lock, matching waitResponseSet.
  std::uint32_t &portableResponseWord() { return portableResponseWord_; }

protected:
  Core::Threads::Lock *portableStateLock_ = nullptr;
  std::uint32_t portableResponseWord_ = 0;
  presonus::dice::SubsystemState state_;
  presonus::dice::ResponseServices *responseServices_ = nullptr;
};

class Dice3Subsystem : public SysexReceiver {
public:
  Dice3Subsystem();
  ~Dice3Subsystem();
  // Independent setup path: does not perform original lifecycle operations.
  explicit Dice3Subsystem(presonus::dice::BorrowedSubsystemSetup) {}
  // Candidate ordinary return spellings remain declaration-pending.
  void resetDice3();
  // Independent borrowed setup for explicit non-lifecycle source ports.
  void setPortableRuntime(presonus::dice::SubsystemRuntime &runtime) {
    runtime_ = &runtime;
  }
  std::int32_t programSerialData(unsigned int serial, unsigned char unit);
  void receive(const SysexPacket &packet) override;
  bool accepts(const SysexPacket &packet) override;
  std::int32_t uiSetCmd(int rate, int clock);
  std::int32_t setRate(Dice3SampleRate rate);
  std::int32_t setClockSource(Dice3ClockSource clock);
  std::int32_t setRoute(Dice3AudioSinkDevice sinkDevice, Dice3AudioSink sink,
                        Dice3AudioSourceDevice sourceDevice,
                        Dice3AudioSource source);
  // Unsynchronized references are for single-thread fixtures/setup only.
  // Concurrent production uses guarded operations and value snapshots.
  presonus::dice::SubsystemState &portableState() { return state_; }
  void setPortableServices(presonus::dice::SubsystemServices &services) {
    services_ = &services;
  }

private:
  presonus::dice::SubsystemRuntime *runtime_ = nullptr;
  presonus::dice::SubsystemServices *services_ = nullptr;
};
} // namespace Presonus::DICE
