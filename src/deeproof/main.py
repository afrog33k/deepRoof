# Utilities
import random
import logging
import time
from timeit import default_timer as timer

# Libraries
import numpy as np
import torch
import torch.optim as optim
import torch.nn.functional as F
from torchvision import transforms

# Custom imports
from deeproof.common import DATA_DIR, IMAGE_DIR, SNAPSHOT_DIR, SUBMISSION_DIR, setup_logs
from deeproof.neuro.handcraft import ResNet, ShortNet
from deeproof.neuro.dpn import DPN26
from deeproof.metrics import SmoothF2Loss
from deeproof.dataset import RoofDataset, train_valid_split
from deeproof.model_handler import DeepRoofHandler


if __name__ == "__main__":
    # Initiate timer:
    global_timer = timer()

    # Setup logs
    run_name = time.strftime("%Y-%m-%d_%H%M-") + "resnet18"
    logger = setup_logs(SNAPSHOT_DIR, run_name)

    # Setting random seeds for reproducibility. (Caveat, some CuDNN algorithms are non-deterministic)
    torch.manual_seed(1337)
    # torch.cuda.manual_seed(1337)
    np.random.seed(1337)
    random.seed(1337)

    ##### Preprocessing parameters: #####

    # Normalization on ImageNet mean/std for finetuning
    normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                     std=[0.229, 0.224, 0.225])

    image_size = 224

    # Augmentation + Normalization for full training
    ds_transform_augmented = transforms.Compose([
        transforms.RandomResizedCrop(image_size),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.ColorJitter(),  # Randomly change the brightness, contrast and saturation of an image.
        transforms.RandomRotation(10),
        transforms.ToTensor(),
        normalize,
    ])

    # Normalization only for validation and test
    ds_transform_raw = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        normalize
    ])

    dr = DeepRoofHandler(logger, ds_transform_augmented, ds_transform_raw)

    ##### Model parameters: #####
    # model = ResNet(num_classes=4, resnet=18)
    model = ResNet(num_classes=4, resnet=50)
    # model = DPN26()

    # criterion = ConvolutedLoss()
    weight = torch.Tensor([1., 1.971741, 3.972452, 1.824547])
    # criterion = torch.nn.MultiLabelSoftMarginLoss(weight=weight)
    # criterion = SmoothF2Loss()
    criterion = torch.nn.CrossEntropyLoss(weight=weight)

    # Note, p_training has lr_decay automated
    optimizer = optim.SGD(model.parameters(), lr=1e-2, momentum=0.9,
                          weight_decay=0.0005)  # Finetuning whole model

    # Training:
    dr.train(epochs=45, model=model, loss_func=criterion, optimizer=optimizer)


    # Predict
    id_model = dr.dbmodel.get_id_model(model, optimizer, criterion,
                                       ds_transform_augmented, ds_transform_raw)
    dr.predict(id_model, model)

    end_global_timer = timer()
    logger.info("################## Success #########################")
    logger.info("Total elapsed time: %s" % (end_global_timer - global_timer))
