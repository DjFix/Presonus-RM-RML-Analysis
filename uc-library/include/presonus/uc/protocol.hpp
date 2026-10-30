#pragma once
#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>

namespace presonus::uc {
using Bytes = std::vector<std::uint8_t>;
inline constexpr std::size_t max_event_size = 0x4000;
constexpr std::uint16_t tag(char a, char b) {
  return (static_cast<std::uint16_t>(static_cast<unsigned char>(a)) << 8) |
         static_cast<unsigned char>(b);
}
enum class EventType : std::uint16_t {
  discovery_alive = tag('D', 'A'),
  discovery_query = tag('D', 'Q'),
  discovery_leave = tag('D', 'L'),
  keep_alive = tag('K', 'A'),
  no_op = tag('N', 'O'),
  param_value = tag('P', 'V'),
  param_edit = tag('P', 'E'),
  param_string = tag('P', 'S'),
  param_mode = tag('P', 'M'),
  param_increment = tag('P', 'I'),
  param_color = tag('P', 'C'),
  param_range = tag('P', 'R'),
  param_string_list = tag('P', 'L'),
  meters8 = tag('M', 'B'),
  meters16 = tag('M', 'S'),
  json_message = tag('J', 'M'),
  binary_object = tag('B', 'O'),
  compressed_message = tag('Z', 'M'),
  udp_mapping = tag('U', 'M'),
  file_request = tag('F', 'R'),
  file_data = tag('F', 'D')
};
struct ProtocolError : std::runtime_error {
  using std::runtime_error::runtime_error;
};

// Original EventClass::write emits type in BE, then two LE 16-bit route fields.
// Their routing semantics have not yet been recovered; preserve both verbatim.
struct Event {
  std::uint16_t type = 0;
  std::uint16_t route_a = 0;
  std::uint16_t route_b = 0;
  Bytes payload;
};
struct Datagram {
  std::uint16_t reply_port;
  Event event;
};
Bytes encode_event(const Event &event);
Event decode_event(const Bytes &bytes);
Bytes encode_tcp(const Event &event);
Bytes encode_udp(const Datagram &datagram);
Datagram decode_udp(const Bytes &bytes);

// Retains partial TCP headers/bodies and emits complete frames only.
// Invalid input poisons the decoder until reset(), rather than silently
// resyncing.
class StreamDecoder {
public:
  std::vector<Event> feed(const std::uint8_t *data, std::size_t size);
  std::vector<Event> feed(const Bytes &data) {
    return feed(data.data(), data.size());
  }
  void reset() {
    pending_.clear();
    failed_ = false;
  }
  std::size_t pending_bytes() const { return pending_.size(); }

private:
  Bytes pending_;
  bool failed_ = false;
};

// Recovered from server 0xe3fdc / 0xe63a8; uses an independent portable API.
// Path + NUL, LE uint16 index, LE IEEE754 binary32 value.
struct ParamValue {
  std::string path;
  std::uint16_t index;
  float value;
};
Bytes encode_param_value(const ParamValue &value);
ParamValue decode_param_value(const Bytes &bytes);
Event make_param_value(const ParamValue &value, std::uint16_t route_a = 0,
                       std::uint16_t route_b = 0);
Event make_keep_alive(std::uint16_t route_a = 0, std::uint16_t route_b = 0);
} // namespace presonus::uc
