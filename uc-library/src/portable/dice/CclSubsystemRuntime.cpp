#include "core/system/corethread.h"
#include "presonus/dice/subsystem_runtime.hpp"
#include "presonus/dice/sysex.hpp"
#include "presonus/dice/uart_assembly.hpp"
#include <stdexcept>
namespace presonus::dice {
namespace {
thread_local SubsystemRuntime *configured = nullptr;
}
ScopedSubsystemRuntime::ScopedSubsystemRuntime(SubsystemRuntime &runtime)
    : previous_(configured) {
  configured = &runtime;
}
ScopedSubsystemRuntime::~ScopedSubsystemRuntime() { configured = previous_; }
SubsystemRuntime &requireSubsystemRuntime() {
  if (!configured)
    throw std::logic_error(
        "Dice3Subsystem requires scoped runtime before construction");
  return *configured;
}
void CclSubsystemRuntime::bind(Presonus::DICE::Dice3Subsystem &subsystem,
                               Presonus::DICE::Dice3Uart &uart) {
  // Bind synchronization before UART registration can publish this receiver.
  subsystem.setPortableStateLock(stateLock_);
  uart_ = &uart;
  subsystem.setPortableServices(*this);
  subsystem.setPortableResponseServices(response_);
}
std::unique_ptr<ProgrammerOutputPin> CclSubsystemRuntime::makeResetPin() {
  return device_.makeOutputPin(100);
}
void CclSubsystemRuntime::sleepMilliseconds(std::uint32_t milliseconds) {
  Core::Threads::CurrentThread::sleep(milliseconds);
}
void CclSubsystemRuntime::post(Presonus::DICE::SysexPacket &packet) {
  if (!uart_)
    throw std::logic_error("Dice3Subsystem UART is not bound");
  uart_->post(packet);
}
std::uint32_t
CclSubsystemRuntime::waitAck(Presonus::DICE::Dice3Subsystem &receiver,
                             std::int64_t timeout) {
  return receiver.waitAck(timeout);
}
void CclSubsystemRuntime::onIdle(bool) {
  if (!uart_)
    throw std::logic_error("Dice3Subsystem UART is not bound");
  uart_->onIdle();
}
} // namespace presonus::dice
