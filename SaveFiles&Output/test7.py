
#from pytorch_pretrained_bert import BertModel, BertTokenizer
import os
import re
import math
import torch
import numpy as np
import random
import torch.nn as nn
import torch.optim as optim
import torch.utils.data as Data

maxlen = 128
batch_size = 416
max_pred = 5  # 最大被maksed然后预测的个数 max tokens of prediction
n_layers = 1  # encoder的层数
n_heads = 1  # 多头注意力机制头数
d_model = 768  # 中间层维度
d_ff = 768 * 4  # 全连接层的维度 4*d_model, FeedForward dimension
d_k = d_v = 64  # QKV的维度 dimension of K(=Q), V
n_segments = 2  # 一个Batch里面有几个日志语句


torch.manual_seed(0)
torch.cuda.manual_seed(0)
torch.manual_seed(0)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def parse(model_path,input_path,output_class,output_token):   # 输入对应的模型路径，需要解析的文件路径，输出到Parseresult文件夹下，output_class为处理文件的类别，Output_token为属于类别的长度
    word2idx=np.load('../SaveFiles&Output/Cluster/'+ output_class +'/word2idx'+ output_token +'.npy',allow_pickle=True).item()
    idx2word=np.load('../SaveFiles&Output/Cluster/'+ output_class +'/idx2word'+ output_token +'.npy',allow_pickle=True).item()
    vocab_size=len(word2idx)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = vary_bert("parse",vocab_size).to(device)  # 实例化模型
    model.load_state_dict(torch.load(model_path))
    lines = open(input_path)
    line = lines.read()
    lines.close()
    sentences = []  #################存储删去源文件索引的日志语句
    sentences1 = line.lower().split('\n')  ################## 包含索引的文件
    sentences2 = line.lower().split('\n')  # filter '.', ',', '?', '!'  re.sub 正则表达式处理数据
    for sentence in sentences2:
        Index = sentence.find(' ')  # 按数据集格式找到该日志的content
        content = sentence[Index + 1:]
        sentences.append(content)
    token_list = list()
    for sentence in sentences:
        arr = [word2idx[s] for s in re.split(r"[ ](?![^(]*\))",sentence)]
        token_list.append(arr)
    batch = []
    count_index = 0
    while count_index < len(sentences):

        #########tokens_a_index, tokens_b_index = randrange(len(sentences)), randrange(
        ########   len(sentences))  # sample random index in sentences
        tokens_value = token_list[count_index]
        count_index += 1
        ############tokens_a, tokens_b = token_list[tokens_a_index], token_list[tokens_b_index]
        input_ids = [word2idx['[CLS]']] + tokens_value
        ####nput_ids = [word2idx['[CLS]']] + tokens_a + [word2idx['[SEP]']] + tokens_b + [word2idx['[SEP]']]
        #####　segment_ids = [0] * (1 + len(tokens_a) + 1) + [1] * (len(tokens_b) + 1)

        # MASK LM
        #############################  n_pred = min(max_pred,
        #########################################              max(1, int(len(input_ids) * 0.15)))  # 选择一句话中有多少个token要被mask 15 % of tokens in one sentence
        cand_maked_pos = [i for i, token in enumerate(input_ids)
                          if token != word2idx['[CLS]']]  # 排除分隔的CLS和SEP candidate masked position
        masked_tokens, masked_pos = [], []

        for pos in cand_maked_pos[
                   :len(
                       cand_maked_pos)]:  #########################################for pos in cand_maked_pos[:n_pred]:  # 随机打乱后取前n_pred个token做mask
            input_ids = [word2idx['[CLS]']] + tokens_value
            masked_tokens, masked_pos = [], []
            masked_pos.append(pos)
            masked_tokens.append(input_ids[pos])
            origin_input_id=input_ids
            #####masked_tokens.append(input_ids[pos])
            ####if random() < 0.8:  # 80%                    #按Bert论文概率选取mask的方式
            input_ids[pos] = word2idx['[MASK]']  # make mask
            n_pad = maxlen - len(input_ids)
            input_ids.extend([0] * n_pad)  # 填充操作，每个句子的长度是30 余下部分补000000
            batch.append([input_ids, masked_tokens, masked_pos])
            break
    input_ids, masked_tokens, masked_pos, = zip(*batch)  ##########################################解析
    input_ids, masked_tokens, masked_pos, = \
        torch.LongTensor(input_ids), torch.LongTensor(masked_tokens), \
        torch.LongTensor(masked_pos),  # 转换成长整性Tensor
    #### sharing parameter from DataPreprocess
    i = 0
    weight = 1
    x = len(batch)
    template = []
    while i < len(batch):
        semantic_contrbution = []
        variable_pos = []
        clustering = []
        classfication=[]
        n = 1
        l = 0
        m = 0
        p = 1  # [CLS]不会输出到解析结果中
        q = 1
        v = 1
        input_ids, masked_tokens, masked_pos = batch[i]

        print('================================')
        input_ids[masked_pos[0]] = masked_tokens[0]
        print([idx2word[w] for w in input_ids if idx2word[w] != '[PAD]'])
        '''
        while v < len(input_ids):  # 将这条日志语句的模板输出
            if idx2word[input_ids[v]] != '[PAD]':
                template.append(idx2word[input_ids[v]] + ' ')  # 加空格
            v += 1
        '''
        i += 1
        attention_score = model(torch.LongTensor([input_ids]),
                                torch.LongTensor([masked_pos]))
        s=input_ids.index(0)
        while n < input_ids.index(0):
            sum = 0
            g = 1
            while g < s:
                sum += attention_score[g][n]
                g += 1
            semantic_contrbution.append(sum)  #去掉了[CLS]
            n += 1
        while q < n:
            classfication.append(attention_score[q][0:n])
            q+=1
        semantic_std = np.std(semantic_contrbution, ddof=1)
        semantic_mean = np.mean(semantic_contrbution)
        while l < len(semantic_contrbution):

            if (semantic_contrbution[l] - semantic_mean) + weight * semantic_std < 0:
                variable_pos.append(l+1)
            l += 1
        while v < len(input_ids):  # 将这条日志语句的模板输出
            z=idx2word[input_ids[v]]
            #if (bool(re.search(r'\d', z)) or bool(
             #       re.search(r'/', z))):
              #  variable_pos.append(v)
            v += 1
        while m < len(variable_pos):
            input_ids[variable_pos[m]] = 2  # 使用一个数字来代替'<*>'
            m += 1
        while p < len(input_ids):  # 将这条日志语句的模板输出
            if idx2word[input_ids[p]] != '[PAD]':
                template.append(idx2word[input_ids[p]] + ' ')  # 加空格
            p += 1
        template.append('\n')
        '''    #调试代码
        if i == 7:
            break
     
       '''
    o = 0
    with open('../SaveFiles&Output/Parseresult/'+ output_class +'/' + str(output_class) + str(output_token) + '.csv', 'w') as f:
        while o < len(template):
            f.write(template[o])
            o += 1
        f.close()


def vary_bert(stage, vocab_size):

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    '''
    loader = Data.DataLoader(MyDataSet(input_ids, masked_tokens, masked_pos), batch_size, True)
    '''

    def get_attn_pad_mask(seq_q, seq_k):
        batch_size, seq_len = seq_q.size()
        # eq(zero) is PAD token
        pad_attn_mask = seq_q.data.eq(0).unsqueeze(1)  # [batch_size, 1, seq_len]
        return pad_attn_mask.expand(batch_size, seq_len, seq_len)  # [batch_size, seq_len, seq_len]

    def gelu(x):
        """
          Implementation of the gelu activation function.
          For information: OpenAI GPT's gelu is slightly different (and gives slightly different results):
          0.5 * x * (1 + torch.tanh(math.sqrt(2 / math.pi) * (x + 0.044715 * torch.pow(x, 3))))
          Also see https://arxiv.org/abs/1606.08415
        """
        return x * 0.5 * (1.0 + torch.erf(x / math.sqrt(2.0)))

    class Embedding(nn.Module):
        def __init__(self):
            super(Embedding, self).__init__()
            self.tok_embed = nn.Embedding(vocab_size, d_model)  # token embedding
            self.pos_embed = nn.Embedding(maxlen, d_model)  # position embedding
            # segment(token type) embedding
            self.norm = nn.LayerNorm(d_model)

        def forward(self, x):
            seq_len = x.size(1)
            pos = torch.arange(seq_len, dtype=torch.long)
            pos = pos.unsqueeze(0).expand_as(x).to(device)  # [seq_len] -> [batch_size, seq_len]
            embedding = self.tok_embed(x.to(device)) + self.pos_embed(pos.to(device))
            return self.norm(embedding)

    class ScaledDotProductAttention(nn.Module):
        def __init__(self):
            super(ScaledDotProductAttention, self).__init__()

        def forward(self, Q, K, V, attn_mask):
            scores = torch.matmul(Q, K.transpose(-1, -2)) / np.sqrt(
                d_k)  # scores : [batch_size, n_heads, seq_len, seq_len]
            scores.masked_fill_(attn_mask, -1e9)  # Fills elements of self tensor with value where mask is one.
            attn = nn.Softmax(dim=-1)(scores)
            at = attn.squeeze(dim=0).squeeze(dim=0)
            if stage == "parse":
                return at.detach().cpu().numpy()
            # torch.set_printoptions(edgeitems=)
            # print('ATTTTTTTTTTTTTTTTTTTTTTTTTTTN',attn)
            context = torch.matmul(attn, V)
            return context

    class MultiHeadAttention(nn.Module):
        def __init__(self):
            super(MultiHeadAttention, self).__init__()
            self.W_Q = nn.Linear(d_model, d_k * n_heads)
            self.W_K = nn.Linear(d_model, d_k * n_heads)
            self.W_V = nn.Linear(d_model, d_v * n_heads)

        def forward(self, Q, K, V, attn_mask):
            # q: [batch_size, seq_len, d_model], k: [batch_size, seq_len, d_model], v: [batch_size, seq_len, d_model]
            residual, batch_size = Q, Q.size(0)
            # (B, S, D) -proj-> (B, S, D) -split-> (B, S, H, W) -trans-> (B, H, S, W)
            q_s = self.W_Q(Q).view(batch_size, -1, n_heads, d_k).transpose(1, 2).to(
                device)  # q_s: [batch_size, n_heads, seq_len, d_k]
            k_s = self.W_K(K).view(batch_size, -1, n_heads, d_k).transpose(1, 2).to(
                device)  # k_s: [batch_size, n_heads, seq_len, d_k]
            v_s = self.W_V(V).view(batch_size, -1, n_heads, d_v).transpose(1, 2).to(
                device)  # v_s: [batch_size, n_heads, seq_len, d_v]

            attn_mask = attn_mask.unsqueeze(1).repeat(1, n_heads, 1,
                                                      1).to(
                device)  # attn_mask : [batch_size, n_heads, seq_len, seq_len]

            # context: [batch_size, n_heads, seq_len, d_v], attn: [batch_size, n_heads, seq_len, seq_len]
            context = ScaledDotProductAttention()(q_s, k_s, v_s, attn_mask)
            if stage == "parse":
                return context
            context = context.transpose(1, 2).contiguous().view(batch_size, -1,
                                                                n_heads * d_v).to(
                device)  # context: [batch_size, seq_len, n_heads, d_v]
            output = nn.Linear(n_heads * d_v, d_model).to(device)(context).to(device)
            # return nn.LayerNorm(d_model).to(device)(output.to(device)).to(device)
            return nn.LayerNorm(d_model).to(device)(output.to(device) + 0.01 * residual.to(device)).to(
                device)  # output: [batch_size, seq_len, d_model]

    class PoswiseFeedForwardNet(nn.Module):
        def __init__(self):
            super(PoswiseFeedForwardNet, self).__init__()
            self.fc1 = nn.Linear(d_model, d_ff)
            self.fc2 = nn.Linear(d_ff, d_model)

        def forward(self, x):
            # (batch_size, seq_len, d_model) -> (batch_size, seq_len, d_ff) -> (batch_size, seq_len, d_model)
            return self.fc2(gelu(self.fc1(x)))

    class EncoderLayer(nn.Module):
        def __init__(self):
            super(EncoderLayer, self).__init__()
            self.enc_self_attn = MultiHeadAttention()
            self.pos_ffn = PoswiseFeedForwardNet()

        def forward(self, enc_inputs, enc_self_attn_mask):
            enc_outputs = self.enc_self_attn(enc_inputs.to(device), enc_inputs.to(device), enc_inputs.to(device),
                                             enc_self_attn_mask.to(device))  # enc_inputs to same Q,K,V
            if stage == "parse":
                return  enc_outputs
            enc_outputs = self.pos_ffn(enc_outputs).to(device)  # enc_outputs: [batch_size, seq_len, d_model]
            return enc_outputs

    class BERT(nn.Module):
        def __init__(self):
            super(BERT, self).__init__()
            self.embedding = Embedding()
            self.layers = nn.ModuleList([EncoderLayer() for _ in range(n_layers)])
            self.fc = nn.Sequential(
                nn.Linear(d_model, d_model),
                nn.Dropout(0.5),
                nn.Tanh(),
            )
            self.classifier = nn.Linear(d_model, 2)
            self.linear = nn.Linear(d_model, d_model)
            self.activ2 = gelu
            # fc2 is shared with embedding layer
            embed_weight = self.embedding.tok_embed.weight
            self.fc2 = nn.Linear(d_model, vocab_size, bias=False)
            self.fc2.weight = embed_weight

        def forward(self, input_ids, masked_pos):
            output = self.embedding(input_ids.to(device)).to(device)  # [bach_size, seq_len, d_model]
            enc_self_attn_mask = get_attn_pad_mask(input_ids, input_ids).to(device)  # [batch_size, maxlen, maxlen]
            for layer in self.layers:
                # output: [batch_size, max_len, d_model]
                output = layer(output, enc_self_attn_mask)
                if stage == "parse":
                    return output
            # it will be decided by first token(CLS)
            ###   h_pooled = self.fc(output[:, 0])  # [batch_size, d_model]
            ####  logits_clsf = self.classifier(h_pooled)  # [batch_size, 2] predict isNext

            masked_pos = masked_pos[:, :, None].expand(-1, -1, d_model)  # [batch_size, max_pred, d_model]
            h_masked = torch.gather(output.to(device), 1,
                                    masked_pos.to(
                                        device))  # masking position [batch_size, max_pred, d_model]  位置对齐，将masked的和原本的token对齐
            h_masked = self.activ2(self.linear(h_masked))  # [batch_size, max_pred, d_model]
            logits_lm = self.fc2(h_masked)  # [batch_size, max_pred, vocab_size]     #
            return logits_lm
    return BERT()

def train(path,epoch_n,output,type,number):
    batch, word2idx, idx2word, vocab_size, word_list, token_list=makedata(1,path)
    np.save('../SaveFiles&Output/Cluster/'+ type +'/word2idx'+ number +'.npy', word2idx)
    np.save('../SaveFiles&Output/Cluster/'+ type +'/idx2word'+ number +'.npy', idx2word)
    input_ids, masked_tokens, masked_pos, = zip(*batch)
    input_ids, masked_tokens, masked_pos, = \
        torch.LongTensor(input_ids), torch.LongTensor(masked_tokens), \
        torch.LongTensor(masked_pos),
    loader = Data.DataLoader(MyDataSet(input_ids, masked_tokens, masked_pos), batch_size, True)
    model = vary_bert("train",vocab_size).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adadelta(model.parameters(), lr=0.01)  # 0.00001
    d=0
    for epoch in range(epoch_n):
        d+=1
        print('=================now you are in =================epoch'+ str(d))
        for input_ids, masked_tokens, masked_pos in loader:
            input_ids, masked_tokens, masked_pos = input_ids.to(device), masked_tokens.to(device), masked_pos.to(device)
            logits_lm = model(input_ids, masked_pos).to(device)
            loss_lm = criterion(logits_lm.view(-1, vocab_size),
                                masked_tokens.view(-1)).to(device)  # for masked LM  Tensor.View元素不变，Tensor形状重构，当某一维为-1时，这一维的大小将自动计算。
            loss_lm = (loss_lm.float()).mean().to(device)
            ######## loss_clsf = criterion(logits_clsf, isNext)  # for sentence classification
            ######## loss = loss_lm + loss_clsf
            loss = loss_lm.to(device)
            if (epoch + 1) % 10 == 0:
                print('Epoch:', '%04d' % (epoch + 1), 'loss =', '{:.6f}'.format(loss))
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
    torch.save(model.state_dict(), '../SaveFiles&Output/modelsave/model'+ str(output))

    # Predict mask tokens ans isNext
    print('============== Train finished==================')

class MyDataSet(Data.Dataset):
    def __init__(self, input_ids, masked_tokens, masked_pos):
        self.input_ids = input_ids
        self.masked_tokens = masked_tokens
        self.masked_pos = masked_pos
    def __len__(self):
        return len(self.input_ids)

    def __getitem__(self, idx):
        return self.input_ids[idx], self.masked_tokens[idx], self.masked_pos[idx]

def makedata(insequence,path):
    print('=========== we are in make data ===========')
    if os.path.exists(path) == True:
        lines = open(path)
        line = lines.read()
        lines.close()
        sentences = []  #################存储删去源文件索引的日志语句
        mid_list=[]
        sentences2 = line.lower().split('\n')  # filter '.', ',', '?', '!'  re.sub
        i=0
        for sentence in sentences2:
            Index = sentence.find(' ')  # 按数据集格式找到该日志的content
            content = sentence[Index + 1:]
            mid_list += list(re.split(r"[ ](?![^(]*\))",content))
            sentences.append(content)
            i+=1
            print('====sentence===='+str(i))
        print('============%%% sentence finished %%==============')
        word_list = list(set(mid_list))
        print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&&')
        '''
        a = 0
        for i in range(len(mid_list)):  ##########################制作无重复词
            if mid_list[i] not in word_list:
                word_list.append(mid_list[i])
            a+=1
            print('====mid list====' + str(a))
        '''
        word2idx = {'[PAD]': 0, '[CLS]': 1, '<*>': 2, '[MASK]': 3}
        b=0
        for i, w in enumerate(word_list):
            word2idx[w] = i + 4
            b+=1
            print('*******enumerate******'+str(b))
        idx2word = {i: w for i, w in enumerate(word2idx)}
        vocab_size = len(word2idx)

        token_list = list()
        c=0
        for sentence in sentences:
            c+=1
            print('%%%%%%%%%%%% final %%%%%%%%%'+str(c))
            arr = [word2idx[s] for s in re.split(r"[ ](?![^(]*\))",sentence)]
            token_list.append(arr)


        print('data test')

        # BERT Parameters
        maxlen = 128
        batch_size = 128
        max_pred = 5  # 最大被maksed然后预测的个数 max tokens of prediction
        n_layers = 1  # encoder的层数
        n_heads = 1  # 多头注意力机制头数
        d_model = 768  # 中间层维度
        d_ff = 768 * 4  # 全连接层的维度 4*d_model, FeedForward dimension
        d_k = d_v = 64  # QKV的维度 dimension of K(=Q), V
        n_segments = 2  # 一个Batch里面有几个日志语句

        batch = []
        count_index = 0
        #############positive = negative = 0
        ################# while positive != batch_size / 2 or negative != batch_size / 2:
        while count_index < len(sentences) and insequence == 0:
            #########tokens_a_index, tokens_b_index = randrange(len(sentences)), randrange(
            ########   len(sentences))  # sample random index in sentences
            tokens_value = token_list[count_index]
            count_index += 1
            ############tokens_a, tokens_b = token_list[tokens_a_index], token_list[tokens_b_index]
            input_ids = [word2idx['[CLS]']] + tokens_value
            ####nput_ids = [word2idx['[CLS]']] + tokens_a + [word2idx['[SEP]']] + tokens_b + [word2idx['[SEP]']]
            #####　segment_ids = [0] * (1 + len(tokens_a) + 1) + [1] * (len(tokens_b) + 1)

            # MASK LM
            #############################  n_pred = min(max_pred,
            #########################################              max(1, int(len(input_ids) * 0.15)))  # 选择一句话中有多少个token要被mask 15 % of tokens in one sentence
            cand_maked_pos = [i for i, token in enumerate(input_ids)
                              if token != word2idx['[CLS]']]  # 排除分隔的CLS和SEP candidate masked position
            random.shuffle(cand_maked_pos)  # 随机打乱过后
            masked_tokens, masked_pos = [], []
            n_pad = maxlen - len(input_ids)
            input_ids.extend([0] * n_pad)  # 填充操作，每个句子的长度是30 余下部分补000000
            ######### segment_ids.extend([0] * n_pad)  # 填充操作，每个句子的长度是30 余下部分补000000

            # Zero Padding (100% - 15%) tokens
            ########if max_pred > n_pred:
            ###########n_pad = max_pred - n_pred
            ###########masked_tokens.extend([0] * n_pad)  # masked的token最大5个，这个数组也要补0000，当你mask数量不足时
            ###############masked_pos.extend([0] * n_pad)

            ##########if tokens_a_index + 1 == tokens_b_index and positive < batch_size / 2:
            batch.append([input_ids, masked_tokens, masked_pos])  # IsNext
            ##############positive += 1
            ########elif tokens_a_index + 1 != tokens_b_index and negative < batch_size / 2:
            ################batch.append([input_ids, segment_ids, masked_tokens, masked_pos, False])  # NotNext
            ######### negative += 1
        while count_index < len(sentences) and insequence == 1:

            #########tokens_a_index, tokens_b_index = randrange(len(sentences)), randrange(
            ########   len(sentences))  # sample random index in sentences
            tokens_value = token_list[count_index]
            count_index += 1
            ############tokens_a, tokens_b = token_list[tokens_a_index], token_list[tokens_b_index]
            d = [word2idx['[CLS]']]
            input_ids = [word2idx['[CLS]']] + tokens_value
            ####nput_ids = [word2idx['[CLS]']] + tokens_a + [word2idx['[SEP]']] + tokens_b + [word2idx['[SEP]']]
            #####　segment_ids = [0] * (1 + len(tokens_a) + 1) + [1] * (len(tokens_b) + 1)

            # MASK LM
            #############################  n_pred = min(max_pred,
            #########################################              max(1, int(len(input_ids) * 0.15)))  # 选择一句话中有多少个token要被mask 15 % of tokens in one sentence
            cand_maked_pos = [i for i, token in enumerate(input_ids)
                              if token != word2idx['[CLS]']]  # 排除分隔的CLS和SEP candidate masked position
            random.shuffle(cand_maked_pos)  # 随机打乱过后
            masked_tokens, masked_pos = [], []

            for pos in cand_maked_pos[
                       :len(
                           cand_maked_pos)]:  #########################################for pos in cand_maked_pos[:n_pred]:  # 随机打乱后取前n_pred个token做mask
                input_ids = [word2idx['[CLS]']] + tokens_value
                masked_tokens, masked_pos = [], []
                masked_pos.append(pos)
                masked_tokens.append(input_ids[pos])
                #####masked_tokens.append(input_ids[pos])

                if random.random() < 0.8:  # 80%                    #按Bert论文概率选取mask的方式
                    input_ids[pos] = word2idx['[MASK]']  # make mask
                elif random.random() > 0.9:  # 百分之十的几率随机替换为其他单词 10%
                    index = random.randint(0, vocab_size - 1)  # random index in vocabulary
                    while index < 4:  # can't involve 'CLS', 'SEP', 'PAD'
                        index = random.randint(0, vocab_size - 1)
                    input_ids[pos] = index  # replace
                ####if random() < 0.8:  # 80%                    #按Bert论文概率选取mask的方式
                # make mask
                n_pad = maxlen - len(input_ids)
                input_ids.extend([0] * n_pad)  # 填充操作，每个句子的长度是30 余下部分补000000
                batch.append([input_ids, masked_tokens, masked_pos])
                break
                # IsNext
                ###############elif random() > 0.9:  # 百分之十的几率随机替换为其他单词 10%
                ###############    index = randint(0, vocab_size - 1)  # random index in vocabulary
                ##############   while index < 4:  # can't involve 'CLS', 'SEP', 'PAD'
                ##############       index = randint(0, vocab_size - 1)
                ##############   input_ids[pos] = index  # replace

            # Zero Paddings

            ######### segment_ids.extend([0] * n_pad)  # 填充操作，每个句子的长度是30 余下部分补000000

            # Zero Padding (100% - 15%) tokens
            ########if max_pred > n_pred:
            ###########n_pad = max_pred - n_pred
            ###########masked_tokens.extend([0] * n_pad)  # masked的token最大5个，这个数组也要补0000，当你mask数量不足时
            ###############masked_pos.extend([0] * n_pad)

            ##########if tokens_a_index + 1 == tokens_b_index and positive < batch_size / 2:

            ##############positive += 1
            ########elif tokens_a_index + 1 != tokens_b_index and negative < batch_size / 2:
            ################batch.append([input_ids, segment_ids, masked_tokens, masked_pos, False])  # NotNext
            ######### negative +=
        print('=========== make data finished ===========')
        return batch,word2idx,idx2word,vocab_size,word_list,token_list
    else:
       print('dataset file not exist')

def paramete(input_file,chose):
    lines = open(input_file)
    line = lines.read()
    lines.close()
    sentences = []  #################存储删去源文件索引的日志语句
    sentences1 = re.sub("[,!?\\-_]", ' ', line.lower()).split('\n')  ################## 包含索引的文件
    sentences2 = line.lower().split('\n')  # filter '.', ',', '?', '!'  re.sub 正则表达式处理数据
    for sentence in sentences2:
        Index = sentence.find(' ')  # 按数据集格式找到该日志的content
        content = sentence[Index + 1:]
        sentences.append(content)
    mid_list = list(re.split(r"[ ](?![^(]*\))"," ".join(sentences)))  # ['hello', 'how', 'are', 'you',...]
    word_list = []

    for i in range(len(mid_list)):  ##########################制作无重复词表

        if mid_list[i] not in word_list:
            word_list.append(mid_list[i])

    word2idx = {'[PAD]': 0, '[CLS]': 1, '<*>': 2, '[MASK]': 3}
    for i, w in enumerate(word_list):
        word2idx[w] = i + 4
    idx2word = {i: w for i, w in enumerate(word2idx)}
    vocab_size = len(word2idx)

    token_list = list()
    for sentence in sentences:
        arr = [word2idx[s] for s in re.split(r"[ ](?![^(]*\))",sentence)]
        token_list.append(arr)
    ##################
    if str(chose) == 'word2idx':
        return word2idx
    if str(chose) == 'idx2word':
        return idx2word
    if str(chose) == 'vocab_size':
        return vocab_size
    if str(chose) == 'word_list':
        return word_list
    if str(chose) == 'token_list':
        return token_list
'''
def embdedding_pretrain(input_path,output_path):
    tokenizer = BertTokenizer.from_pretrained(
        '../Bert/bert-base-uncased-vocab.txt')
    # 加载bert模型，这个路径文件夹下有bert_config.json配置文件和model.bin模型权重文件
    model = BertModel.from_pretrained('../Bert/bert-base-uncased/')
    b1 = open(input_path, encoding='UTF-8')
    a1 = b1.read()
    b1.close()
    line = a1
    sentences = line.lower().split('\n')
    bertembedding = []
    i = 0
    for sentence in sentences:
        marked_text = sentence + " [SEP]"
        tokenized_text = tokenizer.tokenize(marked_text)
        if len(tokenized_text) > 512:
            tokenized_text = tokenizer.tokenize(marked_text)[0:511]
        segments_ids = [1] * len(tokenized_text)
        indexed_tokens = tokenizer.convert_tokens_to_ids(tokenized_text)
        # Convert inputs to PyTorch tensors
        tokens_tensor = torch.tensor([indexed_tokens])
        segments_tensors = torch.tensor([segments_ids])
        print(i)

        with torch.no_grad():
            encoded_layers, _ = model(tokens_tensor, segments_tensors)
            layer_i = 0
            batch_i = 0
            token_i = 0

            # Convert the hidden state embeddings into single token vectors

            # Holds the list of 12 layer embeddings for each token
            # Will have the shape: [# tokens, # layers, # features]
            token_embeddings = []

            # For each token in the sentence...
            for token_i in range(len(tokenized_text)):

                # Holds 12 layers of hidden states for each token
                hidden_layers = []

                # For each of the 12 layers...
                for layer_i in range(len(encoded_layers)):
                    # Lookup the vector for `token_i` in `layer_i`
                    vec = encoded_layers[layer_i][batch_i][token_i]

                    hidden_layers.append(vec)

                token_embeddings.append(hidden_layers)

            # Sanity check the dimensions:
            sentence_embedding = torch.mean(encoded_layers[11], 1).cpu().detach().numpy()
            a = sentence_embedding[0]
            bertembedding.append(sentence_embedding[0])
        i += 1
    a = bertembedding
    np.savetxt(output_path, a)
    print('ok')
'''
def getcontent(input_path, output_path,rgex):      ###########根据日志format 得到日志的content
    lines = open(input_path, encoding='UTF-8')
    line = lines.read()
    lines.close()
    time = 1
    t = 0
    sentences = re.sub("[,!?=]", ' ', line.lower()).split('\n')
    with open(output_path, 'w', encoding='UTF-8') as f:  # 将日志content输出到一个文件夹
        for sentence in sentences:
            if sentence == '':
                continue
            b=re.match(rgex,sentence).group(1)
            content = b
            f.write(str(t) + ' ' + content + '\n')
            t += 1

    f.close()

def getcontentwithoutnumber(input_path, output_path,rgex,choose):      ###########根据日志format 得到日志的content,根据Choose来选择是否保留带数字和/的参数
    lines = open(input_path, encoding='UTF-8')
    line = lines.read()
    lines.close()
    time = 3
    t = 0
    sentences = re.sub("[,!?=]", ' ', line.lower()).split('\n')
    with open(output_path, 'w', encoding='UTF-8') as f:  # 将日志content输出到一个文件夹
        d=0
        for sentence in sentences:
            print('============= you are processing ====== '+ str(d))
            d+=1
            if sentence == '':
                continue
            if re.match(rgex, sentence) != None:
                b = re.match(rgex, sentence).group(1)
                content = b
            else:
                continue
            start =0
            sent="[CLS] "
            content=re.sub('\(.*?\)','',content)
            if choose=='num':
                while content.find(' ', start) != -1:
                    endpos = content.find(' ', start + 1)
                    if endpos == -1:
                        if (bool(re.search(r"[\d](?![^(]*\))", content[start:])) or bool(
                                re.search(r'/', content[start:]))) == False:
                            sent = sent + content[start:]
                        else:
                            sent = sent + ' ' + str(random.randint(0, 100))
                        start = endpos
                        break
                    else:
                        if (bool(re.search(r"[\d](?![^(]*\))", content[start:endpos])) or bool(
                                re.search(r'/', content[start:endpos]))) == False:
                            sent = sent + content[start:endpos]
                        else:
                            sent = sent + ' ' + str(random.randint(0, 100))
                        start = endpos


                marked_text = sent

                f.write(marked_text + '\n')
                t += 1
            else:
                while content.find(' ', start) != -1:
                    endpos = content.find(' ', start + 1)
                    if endpos == -1:
                        if (bool(re.search(r"[\d](?![^(]*\))", content[start:])) or bool(
                                re.search(r'/', content[start:]))) == False:
                            sent = sent + content[start:]
                        start = endpos
                        break
                    else:
                        if (bool(re.search(r"[\d](?![^(]*\))", content[start:endpos])) or bool(
                                re.search(r'/', content[start:endpos]))) == False:
                            sent = sent + content[start:endpos]
                        start = endpos

                marked_text = sent

                f.write(marked_text + '\n')
                t += 1


    f.close()

def train_parse(type,cluster_list):
    lines = open(cluster_list, encoding='UTF-8')
    line = lines.read()
    lines.close()
    for number in line.split('\n'):
        if os.path.exists(str('../SaveFiles&Output/Cluster/')+ type + '/'  + str(type) + number + '.csv') == True:
            print(number)
            train(str('../SaveFiles&Output/Cluster/')+ type + '/'  + str(type) + number + '.csv', 50,str(type)+number,str(type),number)
            parse('../SaveFiles&Output/modelsave/model' + str(type) + number, str('../SaveFiles&Output/Cluster/')+ type + '/'  + str(type) + number + '.csv',type, number)
        else:
            continue

def parse_from_model():
    i = 0
    while i > -1:
        if os.path.exists(str('../SaveFiles&Output/Cluster/') + str(type) + str(i) + '.csv') == True:
            print(i)
            parse('../SaveFiles&Output/modelsave/model'+ str(type) + str(i), str('../SaveFiles&Output/Cluster/') + str(type) + str(i) + '.csv', i)
        else:
            break
        i += 1
def parse_certain_cluster(type,i):
        if os.path.exists(str('../SaveFiles&Output/Cluster/')+ type + '/'  + str(type) + str(i) + '.csv') == True:
            print(i)
            parse('../SaveFiles&Output/modelsave/model'+ str(type) + str(i), str('../SaveFiles&Output/Cluster/')+ type + '/'  + str(type) + str(i) + '.csv', type, str(i))
        else:
            print('cluster' + str(i) + '.csv' + 'dosent exist')
def train_certain_cluster(type,i):
    if os.path.exists(str('../SaveFiles&Output/Cluster/')+ type + '/' +type + str(i) + '.csv') == True:
        print(i)
        train(str('../SaveFiles&Output/Cluster/')+ type + '/' +type + str(i) + '.csv', 2000, str(type)+str(i),str(type),str(i))
    else:
        print('cluster' + str(i) + '.csv' + 'dosent exist')
def get_eval_metric(result_path,template_path):
    accurate_event = 0
    lines = open(result_path, encoding='UTF-8')
    line = lines.read()
    lines.close()
    results = line.split('\n')
    lines1 = open(template_path, encoding='UTF-8')
    line1 = lines1.read()
    lines1.close()
    a=len(results)
    for result in results:
        a=result.strip() in line1.strip()
        if a:
           accurate_event+=1
    print('\n === Evaluation Result on ===' + result_path)
    parsing_accuracy=float(accurate_event)/len(results)
    print(parsing_accuracy)

def clusteringwithlen(contentwithoutnumber_path, content_path, output):
        i=0
        n=0
        b1 = open(contentwithoutnumber_path, encoding='UTF-8')  # 加载embedding
        line = b1.read()
        b1.close()
        b2 = open(content_path, encoding='UTF-8')  # 加载embedding
        line2 = b2.read()
        b2.close()
        sentences2 = line2.split('\n')
        sentences = line.split('\n')
        array_len=[]
        for sentence in sentences:
            if len(sentence.split()) <= 1:
                continue
            if str(len(sentence.split())) not in array_len:
                array_len.append(str(len(sentence.split())))
                with open('../SaveFiles&Output/Cluster/' + str(output) + '/array_len.csv', 'a+', encoding='UTF-8') as f:
                    f.write(str(len(sentence.split()))+'\n')
                    f.close()
                i+=1
            f = open('../SaveFiles&Output/Cluster/' + str(output) + '/'+ str(output) + str(len(sentence.split())) + '.csv',
                     'a+')  # 使用‘a'来提醒python用附加模式的方式打开
            f.write(sentences2[n] + '\n')
            f.close()
            n+=1
'''
def parse_realtime(type,i):
    getcontent('../SaveFiles&Output/dataset/HDFS/HDFS2k.log','../SaveFiles&Output/dataset/HDFS/HDFScontent.csv',r'^.+?: (.+)$')
    getcontentwithoutnumber('../SaveFiles&Output/dataset/HDFS/HDFS2k.log', '../SaveFiles&Output/dataset/HDFS/HDFSwithoutnumber.csv',
                            r'^.+?: (.+)$')
    b1 = open(contentwithoutnumber_path, encoding='UTF-8')  # 加载embedding
    line = b1.read()
    b1.close()
    sentences=line.split()
    for sentence in sentences:
        if len(sentence.split()) > 1 and os.path.exists('../SaveFiles&Output/modelsave/model' + str(type) + str(len(sentence.split()))) == True:
            parse('../SaveFiles&Output/modelsave/model' + str(type) + str(len(sentence.split())),
                  str('../SaveFiles&Output/Cluster/') + type + '/' + str(type) + str(len(sentence.split())) + '.csv', type, i) 
            
        f = open('../SaveFiles&Output/Cluster/' + str(output) + '/' + str(output) + str(len(sentence.split())) + '.csv',
                 'a+')  # 使用‘a'来提醒python用附加模式的方式打开
        f.write(sentences2[n] + '\n')
        f.close()
        n += 1
    
    if os.path.exists(str('../SaveFiles&Output/Cluster/') + type + '/' + str(type) + str(i) + '.csv') == True:
        print(i)
        parse('../SaveFiles&Output/modelsave/model' + str(type) + str(i),
              str('../SaveFiles&Output/Cluster/') + type + '/' + str(type) + str(i) + '.csv', type, i)
    else:
        print('cluster' + str(i) + '.csv' + 'dosent exist')


batch, word2idx, idx2word, vocab_size, word_list, token_list=makedata(1,'../SaveFiles&Output/Cluster/HDFS/HDFS3.csv')
np.save('../SaveFiles&Output/Cluster/word2idx.npy',word2idx)
file=open('../SaveFiles&Output/Cluster/token_list.txt','w')
for token in token_list:
    file.write(str(token))
    file.write('\n')
file.close()
np.save('../SaveFiles&Output/Cluster/idx2word.npy',idx2word)
'''
#train_certain_cluster('HDFS',23)
#parse_certain_cluster('HDFS','4')
#train_parse('Proxifier','../SaveFiles&Output/Cluster/Proxifier/array_len.csv')
#clusteringwithlen('../SaveFiles&Output/dataset/HDFS/HDFSwithoutnumber.csv','../SaveFiles&Output/dataset/HDFS/HDFScontent.csv', 'HDFS')
#train_certain_cluster('Proxifier',)
#getcontent('../SaveFiles&Output/dataset/HDFS/HDFS2k.log','../SaveFiles&Output/dataset/HDFS/HDFScontent.csv',r'^.+?: (.+)$')
#getcontentwithoutnumber('../SaveFiles&Output/dataset/HDFS/HDFS2k.log','../SaveFiles&Output/dataset/HDFS/HDFSwithoutnumber.csv',r'^.+?: (.+)$','nonum')
#getcontentwithoutnumber('../SaveFiles&Output/dataset/HDFS/HDFS2k.log','../SaveFiles&Output/dataset/HDFS/HDFScontent.csv',r'^.+?: (.+)$','num')
#get_eval_metric('../SaveFiles&Output/Parseresult/HDFS/HDFS8.csv','../SaveFiles&Output/Parseresult/HDFS/template.csv')