python3 vaylaAssumeRoleAWSCLI.py --username K954799 --account 043931847925 --role KuvatietoAdmin


aws s3 ls s3://kuvatietovarasto-layersapi-dev --profile vaylaiam


https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up-git-remote-codecommit.html


                        https://git-codecommit.eu-west-1.amazonaws.com/v1/repos/kuvatieto-vieraslaji-docker

git clone codecommit://vaylaiam@git-codecommit.eu-west-1.amazonaws.com/v1/repos/kuvatieto-vieraslaji-docker kuvatieto-vieraslaji-docker
git clone codecommit://kuvatieto-dev@git-codecommit.eu-west-1.amazonaws.com/v1/repos/kuvatieto-vieraslaji-docker kuvatieto-vieraslaji-docker

git remote add origin codecommit://vaylaiam@git-codecommit.eu-west-1.amazonaws.com/v1/repos/kuvatieto-vieraslaji-docker


            "command": ["git config --global credential.helper '!aws codecommit credential-helper $@' && git config --global credential.UseHttpPath true && git clone https://git-codecommit.eu-west-1.amazonaws.com/v1/repos/kuvatieto-vieraslaji-docker kuvatieto-vieraslaji-docker && cd /kuvatieto-vieraslaji-docker && python poll_recognition_queue.py"],


