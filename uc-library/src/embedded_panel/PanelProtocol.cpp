#include "presonus/mcu/panel_protocol.hpp"

namespace presonus::mcu::panel {
std::uint32_t crc32(const std::uint8_t *data, std::int32_t count) {
  std::uint32_t state = 0xffffffff;
  for (std::int32_t i = 0; i < count; ++i) {
    state ^= data[i];
    for (int bit = 0; bit < 8; ++bit)
      state = (state >> 1) ^ ((state & 1) ? 0xedb88320u : 0u);
  }
  return ~state;
}
std::array<std::uint8_t, 2> checksum(const std::uint8_t *data,
                                     std::size_t count) {
  unsigned a = 0, b = 0;
  for (std::size_t i = 0; i < count; ++i) {
    a = (a + data[i]) % 255;
    b = (b + a) % 255;
  }
  return {static_cast<std::uint8_t>(a), static_cast<std::uint8_t>(b)};
}
std::array<std::uint8_t, 14> update_header(std::uint8_t opaque_tag,
                                           std::uint32_t length,
                                           std::uint32_t crc) {
  std::array<std::uint8_t, 14> result{0, 0x27, 9, opaque_tag};
  for (unsigned i = 0; i < 4; ++i) {
    result[4 + i] = static_cast<std::uint8_t>(length >> (8 * i));
    result[8 + i] = static_cast<std::uint8_t>(crc >> (8 * i));
  }
  const auto check = checksum(result.data(), 12);
  result[12] = check[0];
  result[13] = check[1];
  return result;
}
static std::array<std::uint8_t, 5> simple_frame(std::uint8_t code) {
  std::array<std::uint8_t, 5> result{0, code, 0};
  const auto check = checksum(result.data(), 3);
  result[3] = check[0];
  result[4] = check[1];
  return result;
}
std::array<std::uint8_t, 5> control_frame() { return simple_frame(0x26); }
std::array<std::uint8_t, 5> version_query_frame() { return simple_frame(0xa5); }
std::int32_t transfer_result(std::int32_t result) {
  return result > 0 ? 0 : -1;
}
std::int32_t control_result(std::uint32_t result) { return result ? 0 : -1; }
std::uint8_t query_reply_byte(const std::uint8_t *received, std::size_t count) {
  return count >= 4 ? received[3] : 0xff;
}

StepEffect state_step(Descriptor &d, std::uint32_t raw_status,
                      std::uint32_t incoming_data, std::uint8_t outgoing_byte) {
  StepEffect effect;
  std::uint32_t clear = 0x3c;
  const auto transmit = [&] {
    if (d.tx_remaining) {
      effect.data_write = true;
      effect.data = outgoing_byte;
      ++d.tx_pointer;
      --d.tx_remaining;
    } else if (d.rx_remaining) {
      clear = 0x1c;
    } else {
      d.status = 0;
      clear = 0x2c;
    }
  };
  const auto receive = [&] {
    if (d.rx_remaining > 1) {
      clear = 0x38;
    } else {
      clear = (d.mode & 2) ? 0x38 : 0x3c;
      if (d.rx_remaining == 0) {
        d.status = 0;
        clear &= ~0x10u;
      }
    }
  };
  switch (raw_status & 0xf8) {
  case 0x08:
  case 0x10:
    effect.data_write = true;
    effect.data = (static_cast<std::uint32_t>(d.target) << 1) |
                  (d.tx_remaining == 0 ? 1u : 0u);
    break;
  case 0x18:
  case 0x28:
    transmit();
    break;
  case 0x20:
  case 0x30:
    if (d.mode & 1)
      transmit();
    else {
      d.status = 2;
      clear = 0x2c;
    }
    break;
  case 0x38:
    d.status = 5;
    break;
  case 0x50:
  case 0x58:
    effect.receive_write = true;
    effect.receive_address = d.rx_pointer++;
    effect.receive_value = static_cast<std::uint8_t>(incoming_data);
    --d.rx_remaining;
    receive();
    break;
  case 0x40:
    receive();
    break;
  case 0x48:
    d.status = 4;
    clear = 0x2c;
    break;
  case 0:
    d.status = 3;
    clear = 0x2c;
    break;
  default:
    d.status = 1;
    clear = 0x2c;
  }
  effect.control_clear = clear;
  effect.control_set = clear ^ 0x3c;
  effect.completed = d.status != 0xff;
  return effect;
}
} // namespace presonus::mcu::panel
