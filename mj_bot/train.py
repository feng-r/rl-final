import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
import tensorflow.keras
from keras.callbacks import ModelCheckpoint, ReduceLROnPlateau, EarlyStopping
from keras.layers import Conv2D, BatchNormalization, \
    Dense, Dropout, Activation, Flatten
from keras.models import Sequential
from keras.optimizers import Adam

matplotlib.use('Agg')

# GPU设置
gpu = tf.config.experimental.list_physical_devices(device_type='GPU')
assert len(gpu) == 1
tf.config.experimental.set_memory_growth(gpu[0], True)

action = "discard"
batch_size = 32  # TODO batch的大小
epochs_num = 20  # TODO epoch的大小


def generator(x, y, batch=batch_size):
    n = len(x)
    i = 0
    while 1:
        x_train = []
        y_train = []
        # 先搞一个batch_size
        for b in range(batch):
            x_train.append(x[i])
            y_train.append(y[i])
            i = (i + 1) % n
        yield np.array(x_train), np.array(y_train)


def load_data(one_hot=False):
    # TODO
    return train_data, train_label, test_data, test_label


def load_extra_data(one_hot=False):
    # TODO
    return train_data, train_label


def my_model():
    model = Sequential()

    # （1个手牌，4个出的牌，4个吃碰杠的牌）×过去7手
    model.add(Conv2D(100, (5, 2), input_shape=(34, 4, 63)))
    model.add(Activation('relu'))
    model.add(BatchNormalization())
    model.add(Dropout(0.5))

    model.add(Conv2D(100, (5, 2)))
    model.add(Activation('relu'))
    model.add(BatchNormalization())
    model.add(Dropout(0.5))

    model.add(Conv2D(100, (5, 2)))
    model.add(Activation('relu'))
    model.add(BatchNormalization())
    model.add(Dropout(0.5))

    model.add(Flatten())
    model.add(Dense(300))
    model.add(Activation('relu'))

    if action == "discard":
        model.add(Dense(34))  # 判断出什么牌
    elif action == "peng":
        model.add(Dense(2))  # 判断碰还是不碰
    elif action == "chi":
        model.add(Dense(4))  # 判断不吃，吃左边、中间、右边
    else:
        assert False
    model.add(Activation('softmax'))
    model.summary()  # 输出网络结构信息

    opt = tensorflow.keras.optimizers.Adam(lr=0.001)
    model.compile(loss='categorical_crossentropy', optimizer=opt,
                  metrics=['accuracy'])

    return model


def pre_train():
    x_train, y_train = load_extra_data()

    # 多分类标签生成
    y_train = tensorflow.keras.utils.to_categorical(y_train)
    # 生成训练数据
    x_train = x_train.astype('int')
    print("x_train.shape:")
    print(x_train.shape)
    print("\ny_train.shape:")
    print(y_train.shape)

    # TODO
    x_test = x_train[aa:bb]
    y_test = y_train[aa:bb]
    x_pretrain = x_train[0:cc]
    y_pretrain = y_train[0:cc]

    # 生成训练数据
    x_pretrain = x_pretrain.astype('int')
    x_test = x_test.astype('int')
    print("Shapes below:")
    print("x_pretrain.shape:", x_pretrain.shape)
    print("y_pretrain.shape:", y_pretrain.shape)
    print("x_test.shape:", x_test.shape)
    print("y_test.shape:", y_test.shape)

    model = my_model()

    ############################################################################

    num_val = 30000
    num_train = 500000

    # 保存的方式，3世代保存一次
    checkpoint_period1 = ModelCheckpoint(
        "./models" + 'ep{epoch:03d}-loss{loss:.3f}-val_loss{val_loss:.3f}.h5',
        monitor='val_accuracy',
        save_weights_only=False,
        save_best_only=True,
        period=3
    )
    # 学习率下降的方式，acc三次不下降就下降学习率继续训练
    reduce_lr = ReduceLROnPlateau(
        monitor='val_accuracy',
        factor=0.5,
        patience=3,
        verbose=1
    )
    # 是否需要早停，当val_loss一直不下降的时候意味着模型基本训练完毕，可以停止
    early_stopping = EarlyStopping(
        monitor='val_loss',
        min_delta=0,
        patience=10,
        verbose=1
    )

    # 交叉熵
    model.compile(loss='categorical_crossentropy',
                  optimizer=Adam(lr=1e-3),
                  metrics=['accuracy'])

    hist = model.fit_generator(
        generator(x_pretrain[:num_train], y_pretrain[:num_train], batch_size),
        steps_per_epoch=max(1, num_train // batch_size),
        validation_data=generator(x_test, y_test, batch_size),
        validation_steps=max(1, num_val // batch_size),
        epochs=epochs_num,
        initial_epoch=0,
        callbacks=[checkpoint_period1, reduce_lr, early_stopping]
    )

    ############################################################################

    # 保存模型和训练结果

    model.save('./model_pretrain.hdf5')
    model.save_weights('./model_weight_pretrain.hdf5')
    print('testing')
    model.evaluate(x=x_test, y=y_test, batch_size=batch_size, verbose=2)

    # 输出模型结构
    print(model.summary())

    # 输出训练结果
    hist_dict = hist.history
    print("train acc:")
    print(hist_dict['accuracy'])
    print("validation acc:")
    print(hist_dict['val_accuracy'])

    train_acc = hist.history['accuracy']
    val_acc = hist.history['val_accuracy']
    train_loss = hist.history['loss']
    val_loss = hist.history['val_loss']

    # 绘图
    epochs = range(1, len(train_acc) + 1)
    plt.plot(epochs, train_acc, 'bo', label='Training acc')
    plt.plot(epochs, val_acc, 'r', label='Validation acc')
    plt.title('Training and validation accuracy')
    plt.legend()
    plt.savefig("accuracy_pretrain.png")
    plt.figure()  # 新建一个图
    plt.plot(epochs, train_loss, 'bo', label='Training loss')
    plt.plot(epochs, val_loss, 'r', label='Validation loss')
    plt.title('Training and validation loss')
    plt.legend()
    plt.savefig("loss_pretrain.png")

    print("Pre-train finish.")
    del x_pretrain, y_pretrain, x_test, y_test


def train():
    # 数据载入
    x_train, y_train, x_test, y_test = load_data()

    # 多分类标签生成
    y_train = tensorflow.keras.utils.to_categorical(y_train)
    y_test = tensorflow.keras.utils.to_categorical(y_test)
    # 生成训练数据
    x_train = x_train.astype('float32')
    x_test = x_test.astype('float32')
    x_train /= 255
    x_test /= 255
    print(x_train.shape)
    print(y_train.shape)
    print(x_test.shape)
    print(y_test.shape)

    model = my_model()

    model.load_weights('./xxx')  # TODO
    # hist = model.fit_generator(
    #     train_datagan.flow(x_train, y_train, batch_size=batch_size),
    #     steps_per_epoch=x_train.shape[0] // batch_size,
    #     epochs=epochs_num,
    #     validation_data=(x_test, y_test),
    #     shuffle=True
    # )
    hist = model.fit(x_train, y_train, batch_size=batch_size, epochs=epochs_num,
                     validation_data=(x_test, y_test), shuffle=True)

    # 保存模型和训练结果
    model.save('./model1.0.hdf5')
    model.save_weights('./model_weight1.0.hdf5')
    print('testing')
    model.evaluate(x=x_test, y=y_test, batch_size=batch_size, verbose=2)

    # 输出模型结构
    print(model.summary())

    # 输出训练结果
    hist_dict = hist.history
    print("train acc:")
    print(hist_dict['accuracy'])
    print("validation acc:")
    print(hist_dict['val_accuracy'])

    train_acc = hist.history['accuracy']
    val_acc = hist.history['val_accuracy']
    train_loss = hist.history['loss']
    val_loss = hist.history['val_loss']

    # 绘图
    epochs = range(1, len(train_acc) + 1)
    plt.plot(epochs, train_acc, 'bo', label='Training acc')
    plt.plot(epochs, val_acc, 'r', label='Validation acc')
    plt.title('Training and validation accuracy')
    plt.legend()
    plt.savefig("accuracy.png")
    plt.figure()  # 新建一个图
    plt.plot(epochs, train_loss, 'bo', label='Training loss')
    plt.plot(epochs, val_loss, 'r', label='Validation loss')
    plt.title('Training and validation loss')
    plt.legend()
    plt.savefig("loss.png")

    del x_train, y_train, x_test, y_test


pre_train()
train()

# X_train, Y_train, X_test, Y_test = load_data(one_hot = True)
