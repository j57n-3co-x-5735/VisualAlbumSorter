class Vasort < Formula
  desc "Visual Album Sorter – on-device album automation"
  homepage "https://github.com/your-org/visualalbumsorter"
  url "https://github.com/your-org/visualalbumsorter/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "INSERT_SHA256"
  license "MIT"

  depends_on "python@3.11"

  def install
    system "python3", "-m", "venv", "build_venv"
    system "build_venv/bin/pip", "install", "."
    (bin/"vasort").write_env_script libexec/"build_venv/bin/vasort", {}
    (bin/"visualalbumsorter").write_env_script libexec/"build_venv/bin/visualalbumsorter", {}
  end

  test do
    system "#{bin}/vasort", "--status"
  end
end
