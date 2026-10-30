#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

// Independent analysis API. Raw MCU code has no recovered C++ names/prototypes.
// These are portable algorithms/models, not a target firmware or device driver.
namespace presonus::mcu::panel {
std::uint32_t crc32(const std::uint8_t *data, std::int32_t count);
std::array<std::uint8_t, 2> checksum(const std::uint8_t *data,
                                     std::size_t count);
std::array<std::uint8_t, 14>
update_header(std::uint8_t opaque_tag, std::uint32_t length, std::uint32_t crc);
std::array<std::uint8_t, 5> control_frame();
std::array<std::uint8_t, 5> version_query_frame();
std::int32_t transfer_result(std::int32_t transport_result);
std::int32_t control_result(std::uint32_t transport_result);
std::uint8_t query_reply_byte(const std::uint8_t *received,
                              std::size_t prefix_bytes_written);

// Logical descriptor fields correspond to guest offsets0,1,2,4,6,8,12.
// Pointer values are guest integers; the model never dereferences device/host
// addresses. No original private C declaration or host/target ABI is claimed.
struct Descriptor {
  std::uint8_t target = 0, mode = 0;
  std::uint16_t status = 0xff, tx_remaining = 0, rx_remaining = 0;
  std::uint32_t tx_pointer = 0, rx_pointer = 0;
};
struct StepEffect {
  bool data_write = false;
  std::uint32_t data = 0;
  bool receive_write = false;
  std::uint32_t receive_address = 0;
  std::uint8_t receive_value = 0;
  std::uint32_t control_set = 0, control_clear = 0;
  bool completed = false;
};
StepEffect state_step(Descriptor &, std::uint32_t raw_status,
                      std::uint32_t incoming_data, std::uint8_t outgoing_byte);
} // namespace presonus::mcu::panel
