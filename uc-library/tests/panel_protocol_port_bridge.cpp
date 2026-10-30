#include "presonus/mcu/panel_protocol.hpp"
#include <iostream>
#include <sstream>
#include <string>
#include <vector>
using namespace presonus::mcu::panel;
static std::vector<std::uint8_t> unhex(const std::string &s) {
  std::vector<std::uint8_t> result;
  if (s == "-")
    return result;
  for (std::size_t i = 0; i < s.size(); i += 2)
    result.push_back(
        static_cast<std::uint8_t>(std::stoul(s.substr(i, 2), nullptr, 16)));
  return result;
}
template <class Bytes> static std::string hex(const Bytes &data) {
  constexpr char digits[] = "0123456789abcdef";
  std::string result;
  for (auto b : data) {
    result += digits[b >> 4];
    result += digits[b & 15];
  }
  return result.empty() ? "-" : result;
}
int main() {
  for (std::string line; std::getline(std::cin, line);) {
    std::istringstream in(line);
    std::string op;
    in >> op;
    if (op == "quit") {
      std::cout << "OK\n" << std::flush;
      return 0;
    }
    if (op == "crc") {
      std::string data;
      std::int32_t count;
      in >> data >> count;
      auto bytes = unhex(data);
      if (count > 0 && static_cast<std::size_t>(count) > bytes.size())
        return 2;
      std::cout << crc32(bytes.data(), count);
    } else if (op == "header") {
      std::uint32_t tag, length, crc;
      in >> tag >> length >> crc;
      std::cout << hex(
          update_header(static_cast<std::uint8_t>(tag), length, crc));
    } else if (op == "control")
      std::cout << hex(control_frame());
    else if (op == "query")
      std::cout << hex(version_query_frame());
    else if (op == "transfer_result") {
      std::int32_t value;
      in >> value;
      std::cout << transfer_result(value);
    } else if (op == "control_result") {
      std::uint32_t value;
      in >> value;
      std::cout << control_result(value);
    } else if (op == "reply") {
      std::string data;
      in >> data;
      auto bytes = unhex(data);
      std::cout << unsigned(query_reply_byte(bytes.data(), bytes.size()));
    } else if (op == "state") {
      unsigned target, mode, status, tx, rx;
      std::uint32_t hw, data, byte, txp, rxp;
      in >> target >> mode >> status >> tx >> rx >> txp >> rxp >> hw >> data >>
          byte;
      Descriptor d{static_cast<std::uint8_t>(target),
                   static_cast<std::uint8_t>(mode),
                   static_cast<std::uint16_t>(status),
                   static_cast<std::uint16_t>(tx),
                   static_cast<std::uint16_t>(rx),
                   txp,
                   rxp};
      auto e = state_step(d, hw, data, static_cast<std::uint8_t>(byte));
      std::cout << d.status << ' ' << d.tx_remaining << ' ' << d.rx_remaining
                << ' ' << d.tx_pointer << ' ' << d.rx_pointer << ' '
                << e.data_write << ' ' << e.data << ' ' << e.receive_write
                << ' ' << e.receive_address << ' ' << unsigned(e.receive_value)
                << ' ' << e.control_set << ' ' << e.control_clear << ' '
                << e.completed;
    } else
      return 3;
    std::cout << '\n' << std::flush;
  }
}
