#ifdef NDEBUG
#undef NDEBUG
#endif
#include "core/system/corethread.h"
#include "core/system/coretime.h"
#include "presonus/dice/codec.hpp"
#include "presonus/dice/manager.hpp"
#include "presonus/dice/subsystem_runtime.hpp"
#include "presonus/dice/sysex.hpp"
#include "presonus/dice/uart_assembly.hpp"
#include <atomic>
#include <cassert>
#include <iostream>
#include <stdexcept>
#include <thread>
using Presonus::DICE::Dice3Subsystem;
using Presonus::DICE::SysexPacket;
namespace {
void requireUnlocked(Core::Threads::Lock &lock) {
  bool available = false;
  std::thread probe([&] {
    available = lock.tryLock();
    if (available)
      lock.unlock();
  });
  probe.join();
  assert(available);
}
SysexPacket infoPacket(std::uint32_t generation) {
  SysexPacket packet;
  packet.length = 19;
  packet.bytes[0] = 0xf0;
  packet.bytes[1] = 1;
  packet.bytes[2] = 1;
  packet.bytes[18] = 0xf7;
  ::pack32(generation, packet.bytes.data() + 3);
  ::pack32(~generation, packet.bytes.data() + 8);
  ::pack32(generation ^ 0x5a5a5a5aU, packet.bytes.data() + 13);
  return packet;
}
void checkInfo(const std::array<std::uint32_t, 3> &words) {
  assert(words[1] == ~words[0]);
  assert(words[2] == (words[0] ^ 0x5a5a5a5aU));
}
struct Callbacks final : presonus::dice::AssemblyCallbacks {
  void noReceiver(unsigned) override { assert(false); }
  void packetLog(const SysexPacket &) override { assert(false); }
  void sourcePortError(presonus::dice::AssemblyError, unsigned) override {
    assert(false);
  }
};
struct Routes final : presonus::dice::RouteSink {
  std::int32_t setRoute(const presonus::dice::RouteTuple &) override {
    assert(false);
    return -99;
  }
};
struct Device final : presonus::dice::ProgrammerDeviceServices {
  unsigned calls = 0;
  std::int32_t openDevice(const char *, int) override {
    ++calls;
    throw std::logic_error("unexpected device open");
  }
  std::int32_t modeIoctl(std::int32_t, std::uint32_t,
                         std::uint32_t &) override {
    ++calls;
    throw std::logic_error("unexpected ioctl");
  }
  std::int32_t closeDevice(std::int32_t) override {
    ++calls;
    throw std::logic_error("unexpected device close");
  }
  std::unique_ptr<presonus::dice::ProgrammerOutputPin>
  makeOutputPin(int) override {
    ++calls;
    throw std::logic_error("unexpected GPIO");
  }
};
struct ManagerClock final : presonus::dice::ManagerServices {
  Core::Threads::Lock &lock;
  unsigned probes = 0;
  std::atomic<bool> *sleepEntered = nullptr;
  explicit ManagerClock(Core::Threads::Lock &l) : lock(l) {}
  std::int64_t clockRawTicks() override {
    if (probes++ < 2)
      requireUnlocked(lock);
    return Core::SystemClock::getTime();
  }
  void sleepMilliseconds(std::uint32_t ms) override {
    if (sleepEntered && !sleepEntered->load(std::memory_order_acquire)) {
      requireUnlocked(lock);
      sleepEntered->store(true, std::memory_order_release);
    }
    Core::Threads::CurrentThread::sleep(ms);
  }
  void terminateThread() override { assert(false); }
};
struct Pump final : presonus::dice::IdlePump {
  Core::Threads::Lock &lock;
  std::atomic<bool> entered{false};
  unsigned calls = 0;
  explicit Pump(Core::Threads::Lock &l) : lock(l) {}
  void onIdle(bool) override {
    // Before releasing the publisher there is no other state-lock owner.
    if (!entered.load(std::memory_order_acquire))
      requireUnlocked(lock);
    ++calls;
    entered.store(true, std::memory_order_release);
  }
};
struct Commands final : presonus::dice::SubsystemServices {
  Core::Threads::Lock &lock;
  unsigned posts = 0, waits = 0;
  explicit Commands(Core::Threads::Lock &l) : lock(l) {}
  void post(SysexPacket &) override {
    requireUnlocked(lock);
    ++posts;
  }
  std::uint32_t waitAck(Dice3Subsystem &receiver, std::int64_t) override {
    requireUnlocked(lock);
    ++waits;
    SysexPacket ack;
    ack.length = 3;
    ack.bytes[1] = 17;
    ack.bytes[2] = 1;
    receiver.receive(ack);
    return 1;
  }
};
} // namespace
int main() {
  constexpr unsigned generations = 20000, reads = 12000;
  unsigned commandCallbacks = 0, pumpCallbacks = 0;
  {
    Core::Threads::Lock lock;
    Callbacks callbacks;
    presonus::dice::UartAssemblyState uartState({}, 0, 0);
    Presonus::DICE::Dice3Uart uart(uartState, callbacks);
    Device device;
    presonus::dice::CclSubsystemRuntime runtime(device, &lock);
    Dice3Subsystem receiver(presonus::dice::BorrowedSubsystemSetup{});
    runtime.bind(receiver, uart);
    assert(device.calls == 0);
    Commands commands(lock);
    receiver.setPortableServices(commands);
    Routes routes;
    Presonus::DICE::Dice3Manager manager(routes);
    ManagerClock clock(lock);
    manager.setPortableRuntime(receiver, uart, clock);
    receiver.receive(infoPacket(1));
    Presonus::DICE::DiceInfo warmup;
    assert(manager.getDice3Info(&warmup) == 0);
    checkInfo({warmup.portableWords[0], warmup.portableWords[1],
               warmup.portableWords[2]});
    // A waiting getInfo must release its state lock before the clock/sleep
    // callback lets the sole publisher produce a complete response.
    receiver.markPortableInfoPending();
    std::atomic<bool> sleepEntered{false};
    clock.sleepEntered = &sleepEntered;
    std::thread pendingPublisher([&] {
      while (!sleepEntered.load(std::memory_order_acquire))
        std::this_thread::yield();
      receiver.receive(infoPacket(1));
    });
    assert(manager.getDice3Info(&warmup) == 0);
    pendingPublisher.join();
    clock.sleepEntered = nullptr;
    checkInfo({warmup.portableWords[0], warmup.portableWords[1],
               warmup.portableWords[2]});
    std::atomic<bool> go{false}, finished{false};
    std::atomic<unsigned> published{0};
    std::thread writer([&] {
      while (!go.load(std::memory_order_acquire))
        std::this_thread::yield();
      for (unsigned i = 1; i <= generations; ++i) {
        receiver.receive(infoPacket(i));
        published.store(i, std::memory_order_release);
        if ((i & 15) == 0)
          std::this_thread::yield();
      }
      finished.store(true, std::memory_order_release);
    });
    go.store(true, std::memory_order_release);
    unsigned overlapping = 0;
    for (unsigned i = 0; i < reads; ++i) {
      const auto snapshot = receiver.snapshotPortableState();
      checkInfo(snapshot.infoWords);
      Presonus::DICE::DiceInfo info;
      assert(manager.getDice3Info(&info) == 0);
      checkInfo({info.portableWords[0], info.portableWords[1],
                 info.portableWords[2]});
      if (!finished.load(std::memory_order_acquire))
        ++overlapping;
    }
    writer.join();
    assert(overlapping > 0 && published.load() == generations);
    const auto before = receiver.snapshotPortableState();
    receiver.markPortableInfoPending();
    const auto pending = receiver.snapshotPortableState();
    assert(pending.infoWords[0] == 0xffffffffU &&
           pending.infoWords[1] == before.infoWords[1] &&
           pending.infoWords[2] == before.infoWords[2]);
    receiver.receive(infoPacket(generations));
    assert(receiver.setRate(static_cast<Presonus::DICE::Dice3SampleRate>(2)) ==
           0);
    assert(receiver.setClockSource(
               static_cast<Presonus::DICE::Dice3ClockSource>(24)) == 0);
    assert(receiver.setRoute(
               static_cast<Presonus::DICE::Dice3AudioSinkDevice>(1),
               static_cast<Presonus::DICE::Dice3AudioSink>(0),
               static_cast<Presonus::DICE::Dice3AudioSourceDevice>(1),
               static_cast<Presonus::DICE::Dice3AudioSource>(0)) == 0);
    commandCallbacks = commands.posts + commands.waits;
    assert(commandCallbacks == 6);
    Pump pump(lock);
    presonus::dice::CclResponseServices responses(pump);
    receiver.setPortableResponseServices(responses);
    SysexPacket clear;
    clear.length = 3;
    clear.bytes[1] = 0;
    clear.bytes[2] = 0;
    receiver.receive(clear);
    std::thread ackWriter([&] {
      while (!pump.entered.load(std::memory_order_acquire))
        std::this_thread::yield();
      SysexPacket ack;
      ack.length = 3;
      ack.bytes[1] = 17;
      ack.bytes[2] = 1;
      receiver.receive(ack);
    });
    assert(receiver.waitAck(2000) == 17);
    ackWriter.join();
    assert(receiver.snapshotPortableState().status == 1);
    pump.entered.store(false, std::memory_order_release);
    unsigned int response = 0;
    std::thread responseWriter([&] {
      while (!pump.entered.load(std::memory_order_acquire))
        std::this_thread::yield();
      Core::Threads::ScopedLock guard(lock);
      response = 0x12345678U;
    });
    assert(receiver.waitResponseSet(response, 2000));
    responseWriter.join();
    {
      Core::Threads::ScopedLock guard(lock);
      assert(response == 0x12345678U);
    }
    pumpCallbacks = pump.calls;
    assert(pumpCallbacks >= 2);
    assert(device.calls == 0);
  }
  std::cout << "{\"passed\":true,\"coherent_generations\":" << generations
            << ",\"snapshot_and_manager_reads\":" << reads
            << ",\"command_reentrancy_probes\":" << commandCallbacks
            << ",\"pump_reentrancy_probes\":" << pumpCallbacks
            << ",\"real_ccl_lock_clock_sleep\":true,\"device_operations\":0}"
            << std::endl;
}
