#include "presonus/mcu/update_loop.hpp"
#include <array>

namespace presonus::mcu::panel {
UpdateOutcome run_update_loop(UpdateBoundary &io, std::uint8_t initial_flag) {
  constexpr std::array<std::uint8_t, 5> targets{0x61, 0x60, 0x69, 0x68, 0x6f};
  bool attempted_transfer = false;
  io.interrupts_masked = true;
  io.delay(1600000);
  for (std::uint32_t index = 0; index < targets.size(); ++index) {
    const auto target = targets[index];
    for (unsigned attempt = 0; attempt < 3; ++attempt) {
      std::uint8_t tag = 0xff;
      for (unsigned query_count = 0; query_count < 100 && tag == 0xff;
           ++query_count) {
        io.delay(200000);
        tag = io.query(target);
      }
      if (tag == 0x1b) {
        io.status(index, 0, 0x1b);
        break;
      }
      io.status(index, 1, tag);
      if (tag != 0xfe && tag != 0xff) {
        io.control(target);
        std::uint32_t remaining = 100;
        bool repeat_attempt = false;
        for (;;) {
          const auto before = remaining;
          --remaining;
          // Original carry-clear branch: underflow proceeds to transfer.
          if (before == 0)
            break;
          io.delay(200000);
          if (io.query(target) == 0xfe) {
            // FE on the100th query restarts, unlike never observing FE.
            repeat_attempt = remaining == 0;
            break;
          }
        }
        if (repeat_attempt)
          continue;
      }
      const auto result = io.transfer(target, 0x9e40, 0x2f70, 0x1b);
      attempted_transfer = true;
      if (result == 0) {
        io.status(index, 0, 0x1b);
        break;
      }
      io.status(index, 0x0f, 0);
    }
  }
  io.interrupts_masked = false;
  io.delay(4000000);
  return {0, attempted_transfer ? std::uint8_t{1} : initial_flag,
          attempted_transfer};
}
} // namespace presonus::mcu::panel
