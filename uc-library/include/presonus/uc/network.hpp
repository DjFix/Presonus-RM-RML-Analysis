#pragma once
#include "protocol.hpp"
#include <chrono>

namespace presonus::uc {
// POSIX IPv4 transport. Callers own UC discovery/registration/subscription
// policy. This is a new portable interface, not the binary layout of Presonus
// classes.
class TcpConnection {
public:
  explicit TcpConnection(int fd = -1);
  ~TcpConnection();
  TcpConnection(TcpConnection &&other) noexcept;
  TcpConnection &operator=(TcpConnection &&other) noexcept;
  TcpConnection(const TcpConnection &) = delete;
  TcpConnection &operator=(const TcpConnection &) = delete;
  void send(const Event &event,
            std::chrono::milliseconds timeout = std::chrono::seconds(5));
  std::vector<Event>
  receive(std::chrono::milliseconds timeout = std::chrono::seconds(5));
  bool open() const { return fd_ >= 0; }
  void close() noexcept;

private:
  int fd_;
  StreamDecoder decoder_;
};
class Client {
public:
  static TcpConnection
  connect(const std::string &ipv4, std::uint16_t port,
          std::chrono::milliseconds timeout = std::chrono::seconds(5));
};
class Server {
public:
  explicit Server(std::uint16_t port,
                  const std::string &bind_ipv4 = "127.0.0.1");
  ~Server();
  Server(const Server &) = delete;
  Server &operator=(const Server &) = delete;
  TcpConnection
  accept(std::chrono::milliseconds timeout = std::chrono::seconds(5));
  std::uint16_t port() const;

private:
  int fd_ = -1;
};
} // namespace presonus::uc
