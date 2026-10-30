#include "presonus/dice/uart_assembly.hpp"
#include <atomic>
#include <chrono>
#include <iostream>
#include <stdexcept>
#include <thread>

namespace {
class Receiver : public Presonus::DICE::ISysexReceiver {
public:
  void receive(const Presonus::DICE::SysexPacket &) override {}
  bool accepts(const Presonus::DICE::SysexPacket &) override { return false; }
};
class Callbacks : public presonus::dice::AssemblyCallbacks {
public:
  void noReceiver(unsigned) override {}
  void packetLog(const Presonus::DICE::SysexPacket &) override {}
  void sourcePortError(presonus::dice::AssemblyError, unsigned) override {}
};
void require(bool value) {
  if (!value)
    throw std::runtime_error("registration source-provider assertion");
}
} // namespace

int main(int argc, char **) {
  Receiver receiver[4];
  Presonus::DICE::ISysexReceiver *tokens[] = {nullptr, receiver, receiver + 1,
                                              receiver + 2, receiver + 3};
  const auto token = [&](Presonus::DICE::ISysexReceiver *pointer) {
    for (unsigned i = 0; i < 5; ++i)
      if (tokens[i] == pointer)
        return i;
    throw std::runtime_error("unexpected pointer");
  };
  std::array<unsigned char, 67> seed{};
  Callbacks callbacks;
  if (argc > 1) {
    presonus::dice::UartAssemblyState state(seed, 0, 0);
    Presonus::DICE::Dice3Uart uart(state, callbacks);
    for (int i = 0; i < 128; ++i)
      uart.registerReceiver(tokens[i % 5]);
    require(state.receivers.count() == 128 &&
            state.receivers.getCapacity() >= 128);
    for (int i = 0; i < 128; ++i)
      require(state.receivers.at(i) == tokens[i % 5]);
    while (state.receivers.count())
      uart.unRegisterReceiver(state.receivers.at(0));
    std::atomic<bool> started{false}, finished{false};
    state.lock.lock();
    std::thread worker([&] {
      started = true;
      uart.registerReceiver(receiver);
      uart.unRegisterReceiver(receiver);
      finished = true;
    });
    while (!started)
      std::this_thread::yield();
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
    require(!finished);
    state.lock.unlock();
    worker.join();
    require(finished && state.receivers.count() == 0);
    std::cout << "PASS actual CCL vector growth/duplicates/nulls and locked "
                 "registration/removal\n";
    return 0;
  }
  unsigned total;
  std::cin >> total;
  for (unsigned caseIndex = 0; caseIndex < total; ++caseIndex) {
    std::string name;
    unsigned count, error, operations;
    std::cin >> name >> count >> error >> operations;
    require(count <= 16 && error < 5);
    presonus::dice::UartAssemblyState state(seed, 0, 16);
    for (int i = 0; i < 16; ++i)
      state.receivers.getItems()[i] = tokens[(i + 3) % 5];
    for (unsigned i = 0; i < count; ++i) {
      unsigned value;
      std::cin >> value;
      require(value < 5);
      state.receivers.add(tokens[value]);
    }
    Core::ConstVector<Presonus::DICE::ISysexReceiver *>::getError() =
        tokens[error];
    Presonus::DICE::Dice3Uart uart(state, callbacks);
    std::cout << name << ' ';
    for (unsigned i = 0; i < operations; ++i) {
      char action;
      unsigned value;
      std::cin >> action >> value;
      require(value < 5);
      if (action == 'a') {
        require(state.receivers.count() < 16);
        uart.registerReceiver(tokens[value]);
      } else {
        require(action == 'r');
        uart.unRegisterReceiver(tokens[value]);
      }
      std::cout << state.receivers.count() << ':';
      for (int slot = 0; slot < 16; ++slot)
        std::cout << token(state.receivers.getItems()[slot]) << ',';
      std::cout << ';';
    }
    std::cout << '\n';
  }
  Core::ConstVector<Presonus::DICE::ISysexReceiver *>::getError() = nullptr;
}
