#include "presonus/uc/network.hpp"
#include <arpa/inet.h>
#include <cerrno>
#include <climits>
#include <fcntl.h>
#include <poll.h>
#include <sys/socket.h>
#include <system_error>
#include <unistd.h>
#include <utility>

namespace presonus::uc {
namespace {
using Clock = std::chrono::steady_clock;
[[noreturn]] void error(const char *text) {
  throw std::system_error(errno, std::generic_category(), text);
}
void configure(int fd) {
  int flags = fcntl(fd, F_GETFL, 0);
  if (flags < 0 || fcntl(fd, F_SETFL, flags | O_NONBLOCK) < 0 ||
      fcntl(fd, F_SETFD, FD_CLOEXEC) < 0)
    error("configure socket");
#ifdef SO_NOSIGPIPE
  int one = 1;
  if (setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &one, sizeof(one)) < 0)
    error("SO_NOSIGPIPE");
#endif
}
sockaddr_in address(const std::string &ipv4, std::uint16_t port) {
  sockaddr_in out{};
  out.sin_family = AF_INET;
  out.sin_port = htons(port);
  if (inet_pton(AF_INET, ipv4.c_str(), &out.sin_addr) != 1)
    throw std::invalid_argument("numeric IPv4 address required");
  return out;
}
void wait(int fd, short events, Clock::time_point deadline) {
  for (;;) {
    auto remaining = std::chrono::duration_cast<std::chrono::milliseconds>(
                         deadline - Clock::now())
                         .count();
    if (remaining <= 0)
      throw std::system_error(ETIMEDOUT, std::generic_category(),
                              "UC socket timeout");
    pollfd p{fd, events, 0};
    auto result = poll(
        &p, 1, static_cast<int>(remaining > INT_MAX ? INT_MAX : remaining));
    if (result < 0) {
      if (errno == EINTR)
        continue;
      error("poll");
    }
    if (!result)
      continue;
    if (p.revents & POLLNVAL)
      throw std::system_error(EBADF, std::generic_category(), "invalid socket");
    if (p.revents & (events | POLLHUP | POLLERR))
      return;
  }
}
} // namespace
TcpConnection::TcpConnection(int fd) : fd_(fd) {
  if (fd_ >= 0)
    try {
      configure(fd_);
    } catch (...) {
      ::close(fd_);
      fd_ = -1;
      throw;
    }
}
TcpConnection::~TcpConnection() { close(); }
TcpConnection::TcpConnection(TcpConnection &&other) noexcept
    : fd_(std::exchange(other.fd_, -1)), decoder_(std::move(other.decoder_)) {}
TcpConnection &TcpConnection::operator=(TcpConnection &&other) noexcept {
  if (this != &other) {
    close();
    fd_ = std::exchange(other.fd_, -1);
    decoder_ = std::move(other.decoder_);
  }
  return *this;
}
void TcpConnection::close() noexcept {
  if (fd_ >= 0)
    ::close(fd_);
  fd_ = -1;
  decoder_.reset();
}
void TcpConnection::send(const Event &event,
                         std::chrono::milliseconds timeout) {
  if (fd_ < 0)
    throw std::logic_error("connection is closed");
  auto bytes = encode_tcp(event);
  std::size_t offset = 0;
  auto deadline = Clock::now() + timeout;
  try {
    while (offset < bytes.size()) {
      wait(fd_, POLLOUT, deadline);
#ifdef MSG_NOSIGNAL
      constexpr int flags = MSG_NOSIGNAL;
#else
      constexpr int flags = 0;
#endif
      auto n = ::send(fd_, bytes.data() + offset, bytes.size() - offset, flags);
      if (n < 0) {
        if (errno == EINTR || errno == EAGAIN || errno == EWOULDBLOCK)
          continue;
        error("send");
      }
      if (!n)
        throw std::system_error(EPIPE, std::generic_category(),
                                "send returned zero");
      offset += static_cast<std::size_t>(n);
    }
  } catch (...) {
    close();
    throw;
  } // A partially sent frame cannot be safely retried.
}
std::vector<Event> TcpConnection::receive(std::chrono::milliseconds timeout) {
  if (fd_ < 0)
    throw std::logic_error("connection is closed");
  auto deadline = Clock::now() + timeout;
  for (;;) {
    wait(fd_, POLLIN, deadline);
    std::uint8_t buffer[4096];
    auto n = ::recv(fd_, buffer, sizeof(buffer), 0);
    if (n < 0) {
      if (errno == EINTR || errno == EAGAIN || errno == EWOULDBLOCK)
        continue;
      auto saved = errno;
      close();
      errno = saved;
      error("recv");
    }
    if (!n) {
      bool partial = decoder_.pending_bytes() != 0;
      close();
      if (partial)
        throw ProtocolError("peer closed during a UC frame");
      return {};
    }
    try {
      auto events = decoder_.feed(buffer, static_cast<std::size_t>(n));
      if (!events.empty())
        return events;
    } catch (...) {
      close();
      throw;
    }
  }
}
TcpConnection Client::connect(const std::string &ipv4, std::uint16_t port,
                              std::chrono::milliseconds timeout) {
  auto addr = address(ipv4, port);
  int fd = socket(AF_INET, SOCK_STREAM, 0);
  if (fd < 0)
    error("socket");
  try {
    configure(fd);
    if (::connect(fd, reinterpret_cast<sockaddr *>(&addr), sizeof(addr)) < 0) {
      if (errno != EINPROGRESS)
        error("connect");
      wait(fd, POLLOUT, Clock::now() + timeout);
      int code = 0;
      socklen_t length = sizeof(code);
      if (getsockopt(fd, SOL_SOCKET, SO_ERROR, &code, &length) < 0)
        error("connect status");
      if (code)
        throw std::system_error(code, std::generic_category(), "connect");
    }
  } catch (...) {
    ::close(fd);
    throw;
  }
  return TcpConnection(fd);
}
Server::Server(std::uint16_t port, const std::string &ipv4) {
  auto addr = address(ipv4, port);
  fd_ = socket(AF_INET, SOCK_STREAM, 0);
  if (fd_ < 0)
    error("socket");
  try {
    configure(fd_);
    int one = 1;
    if (setsockopt(fd_, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one)) < 0)
      error("SO_REUSEADDR");
    if (bind(fd_, reinterpret_cast<sockaddr *>(&addr), sizeof(addr)) < 0)
      error("bind");
    if (listen(fd_, 16) < 0)
      error("listen");
  } catch (...) {
    ::close(fd_);
    fd_ = -1;
    throw;
  }
}
Server::~Server() {
  if (fd_ >= 0)
    ::close(fd_);
}
TcpConnection Server::accept(std::chrono::milliseconds timeout) {
  auto deadline = Clock::now() + timeout;
  for (;;) {
    wait(fd_, POLLIN, deadline);
    int peer = ::accept(fd_, nullptr, nullptr);
    if (peer >= 0)
      return TcpConnection(peer);
    if (errno != EINTR && errno != EAGAIN && errno != EWOULDBLOCK)
      error("accept");
  }
}
std::uint16_t Server::port() const {
  sockaddr_in addr{};
  socklen_t length = sizeof(addr);
  if (getsockname(fd_, reinterpret_cast<sockaddr *>(&addr), &length) < 0)
    error("getsockname");
  return ntohs(addr.sin_port);
}
} // namespace presonus::uc
