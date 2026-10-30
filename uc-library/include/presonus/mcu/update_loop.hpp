#pragma once
#include "presonus/mcu/panel_protocol.hpp"
#include <cstdint>

namespace presonus::mcu::panel {
// Independent logical boundary API, not original MCU declarations/HAL.
struct UpdateBoundary {
  bool interrupts_masked =
      false; // model state only, never host interrupt control
  virtual ~UpdateBoundary() = default;
  virtual void delay(std::uint32_t count) = 0;
  virtual std::uint8_t query(std::uint8_t target) = 0;
  virtual void control(std::uint8_t target) = 0;
  virtual std::int32_t transfer(std::uint8_t target,
                                std::uint32_t image_pointer,
                                std::uint32_t length, std::uint8_t tag) = 0;
  virtual void status(std::uint32_t target_index, std::uint8_t code,
                      std::uint8_t value) = 0;
};
struct UpdateOutcome {
  std::uint32_t return_value = 0;
  std::uint8_t final_flag = 0;
  bool flag_written = false;
};
UpdateOutcome run_update_loop(UpdateBoundary &, std::uint8_t initial_flag);
} // namespace presonus::mcu::panel
