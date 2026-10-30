#include "presonus/uc/network.hpp"
#include <future>
#include <iostream>
int main() {
  using namespace presonus::uc;
  Server server(0);
  auto task = std::async(std::launch::async, [&] {
    auto peer = server.accept();
    for (const auto &event : peer.receive())
      peer.send(event);
  });
  auto client = Client::connect("127.0.0.1", server.port());
  client.send(make_param_value({"line/ch1", 0, 0.5f}));
  auto events = client.receive();
  auto value = decode_param_value(events.at(0).payload);
  std::cout << value.path << "[" << value.index << "] = " << value.value
            << '\n';
  task.get();
}
