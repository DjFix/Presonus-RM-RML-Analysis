#include "presonus/uc/abi32.hpp"
#include "presonus/uc/network.hpp"
#include <algorithm>
#include <fstream>
#include <future>
#include <iostream>
#include <sstream>
#include <string>

using namespace presonus::uc;
void require(bool ok, const std::string &message) {
  if (!ok)
    throw std::runtime_error(message);
}
Bytes hex(const std::string &value) {
  require(value.size() % 2 == 0, "odd hex length");
  Bytes out;
  for (std::size_t i = 0; i < value.size(); i += 2)
    out.push_back(
        static_cast<std::uint8_t>(std::stoul(value.substr(i, 2), nullptr, 16)));
  return out;
}
template <class F> void rejects(F operation) {
  bool rejected = false;
  try {
    operation();
  } catch (const ProtocolError &) {
    rejected = true;
  }
  require(rejected, "malformed input accepted");
}
int main(int argc, char **argv) {
  try {
    auto event = make_param_value({"line/ch1", 7, 0.5f}, 0x1234, 0x5678);
    const auto golden =
        hex("5543000115005056341278566c696e652f6368310007000000003f");
    require(encode_tcp(event) == golden, "parameter event golden mismatch");
    for (std::size_t split = 0; split <= golden.size(); ++split) {
      StreamDecoder decoder;
      auto first = decoder.feed(golden.data(), split);
      auto second = decoder.feed(golden.data() + split, golden.size() - split);
      require(first.size() + second.size() == 1 && !decoder.pending_bytes(),
              "split stream lost a frame");
    }
    auto combined = golden;
    combined.insert(combined.end(), golden.begin(), golden.end());
    StreamDecoder decoder;
    require(decoder.feed(combined).size() == 2, "coalesced frames failed");
    rejects([&] {
      StreamDecoder d;
      d.feed(hex("554300010500"));
    });
    rejects([&] {
      StreamDecoder d;
      d.feed(hex("554300010140"));
    });
    rejects([&] {
      StreamDecoder d;
      d.feed(hex("554300020600"));
    });
    rejects([&] { decode_udp(hex("554300010000")); });
    rejects([&] { decode_param_value(hex("616263")); });
    rejects([&] { encode_param_value({std::string("a\0b", 3), 0, 0}); });
    rejects([&] { encode_event({0, 0, 0, Bytes(max_event_size)}); });
    rejects(
        [&] { encode_udp({53000, {0, 0, 0, Bytes(max_event_size - 11)}}); });
    StreamDecoder poison;
    rejects([&] { poison.feed(hex("554300020600")); });
    rejects([&] { poison.feed(golden); });
    poison.reset();
    require(poison.feed(golden).size() == 1, "decoder reset failed");
    auto maxframe =
        encode_tcp({0xffff, 0xffff, 0xffff, Bytes(max_event_size - 6, 0xaa)});
    StreamDecoder maxdecoder;
    require(maxdecoder.feed(maxframe).size() == 1, "maximum frame rejected");
    require(argc == 2, "capture vector file is required");
    std::ifstream input(argv[1]);
    require(bool(input), "cannot read capture vectors");
    std::size_t udp = 0, tcp = 0, pv = 0;
    std::string transport, value;
    while (input >> transport >> value) {
      const auto bytes = hex(value);
      Event captured;
      if (transport == "udp") {
        auto datagram = decode_udp(bytes);
        captured = datagram.event;
        require(encode_udp(datagram) == bytes, "captured UDP mismatch");
        ++udp;
      } else {
        require(transport == "tcp", "unknown vector transport");
        StreamDecoder d;
        std::vector<Event> events;
        for (std::size_t offset = 0; offset < bytes.size();) {
          auto count = std::min(std::size_t(7), bytes.size() - offset);
          auto part = d.feed(bytes.data() + offset, count);
          events.insert(events.end(), part.begin(), part.end());
          offset += count;
        }
        require(events.size() == 1 && !d.pending_bytes(),
                "capture frame not decoded");
        captured = events[0];
        require(encode_tcp(captured) == bytes, "captured TCP mismatch");
        ++tcp;
      }
      if (captured.type == std::uint16_t(EventType::param_value)) {
        auto parameter = decode_param_value(captured.payload);
        require(encode_param_value(parameter) == captured.payload,
                "captured parameter value mismatch");
        ++pv;
      }
    }
    require(udp > 0 && tcp > 0 && pv > 0, "capture coverage missing");
    Server server(0);
    auto worker = std::async(std::launch::async, [&] {
      auto peer = server.accept();
      auto received = peer.receive();
      require(received.size() == 1, "loopback receive failed");
      peer.send(received[0]);
    });
    auto client = Client::connect("127.0.0.1", server.port());
    client.send(event);
    auto reply = client.receive();
    require(reply.size() == 1 && encode_event(reply[0]) == encode_event(event),
            "client/server loopback mismatch");
    worker.get();
    std::cout << "PASS: " << udp << " captured UDP, " << tcp
              << " captured TCP, " << pv
              << " parameter payloads; malformed/split/combined/max frames; "
                 "TCP client/server loopback\n";
    return 0;
  } catch (const std::exception &e) {
    std::cerr << "FAIL: " << e.what() << '\n';
    return 1;
  }
}
