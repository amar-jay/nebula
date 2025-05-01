import torch


def status(name, result, info=""):
    check = "✅" if result else "❌"
    print(f"{check} {name.ljust(35)} {info}")


def main():
    print("🔍 PyTorch Environment Diagnostic\n")

    # PyTorch installation
    try:
        import torch

        status("PyTorch Installed", True, f"Version: {torch.__version__}")
    except ImportError:
        status("PyTorch Installed", False)
        return

    # CUDA availability
    cuda_available = torch.cuda.is_available()
    status("CUDA Available", cuda_available)

    # cuDNN availability
    cudnn_available = torch.backends.cudnn.is_available()
    status("cuDNN Available", cudnn_available)

    # CUDA version
    if cuda_available:
        status("CUDA Version", True, torch.version.cuda)
    else:
        status("CUDA Version", False)

    # Number of GPUs
    num_gpus = torch.cuda.device_count()
    status("Number of CUDA Devices", num_gpus > 0, str(num_gpus))

    # GPU Names
    for i in range(num_gpus):
        name = torch.cuda.get_device_name(i)
        status(f"Device {i} Name", True, name)

    # Test tensor operations on CPU and GPU
    try:
        a = torch.randn(1000, 1000)
        b = torch.randn(1000, 1000)
        _ = a @ b
        status("Tensor Ops on CPU", True)
    except:
        status("Tensor Ops on CPU", False)

    if cuda_available:
        try:
            a_gpu = a.cuda()
            b_gpu = b.cuda()
            _ = a_gpu @ b_gpu
            status("Tensor Ops on GPU", True)
        except:
            status("Tensor Ops on GPU", False)

    # Check mixed precision availability
    amp_available = hasattr(torch.cuda, "amp")
    status("AMP (Mixed Precision)", amp_available)

    # Check MPS (Apple Silicon)
    mps_available = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    status("MPS Available (Apple Silicon)", mps_available)

    print("\n✅ Done.")


if __name__ == "__main__":
    main()
