#include "presonus/uc/socket_channel.hpp"
#include <array>
#include <cstdio>
#include <cstdlib>
#include <memory>
using Channel = Presonus::UC::SocketConnection::Channel;
static void require(bool b) {
  if (!b)
    std::abort();
}
struct Derived : Channel {
  std::array<int, 7> &seen;
  unsigned &destroyed;
  Derived(presonus::uc::SocketChannelIO &io, std::array<int, 7> &s, unsigned &d)
      : Channel(io), seen(s), destroyed(d) {}
  bool isReadable(int n) override {
    seen[0] = n;
    return true;
  }
  int getBytesAvailable() override {
    seen[1] = 1;
    return 313;
  }
  int read(void *p, int n) override {
    seen[2] = n;
    if (n > 0)
      *static_cast<unsigned char *>(p) = 0xa7;
    return n;
  }
  bool isWritable(int n) override {
    seen[3] = n;
    return false;
  }
  int getGranularity() override {
    seen[4] = 1;
    return 8192;
  }
  int write(const void *p, int n) override {
    seen[5] = n;
    require(*static_cast<const unsigned char *>(p) == 0xa7);
    return -17;
  }
  bool hasErrors(int n) override {
    seen[6] = n;
    return true;
  }
  ~Derived() override { ++destroyed; }
};
int main() {
  presonus::uc::SocketChannelIO io;
  std::array<int, 7> seen{};
  unsigned destroyed = 0;
  unsigned char data = 0;
  {
    std::unique_ptr<Channel> owner(new Derived(io, seen, destroyed));
    Channel &channel = *owner;
    require(channel.isReadable(-3));
    require(channel.getBytesAvailable() == 313);
    require(channel.read(&data, 1) == 1 && data == 0xa7);
    require(!channel.isWritable(19));
    require(channel.getGranularity() == 8192);
    require(channel.write(&data, 1) == -17);
    require(channel.hasErrors(-7));
    require(seen == std::array<int, 7>{-3, 1, 1, 19, 1, 1, -7} &&
            destroyed == 0);
  }
  require(destroyed == 1);
  std::puts("7 source-native virtual overrides and portable virtual lifetime "
            "helper passed; original D1/D0 semantics unverified");
}
